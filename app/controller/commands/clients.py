from pathlib import Path
from typing import Annotated
from uuid import UUID

from rich.console import Console
from rich.text import Text
from typer import Argument, Context, Option, Exit

from app.cli import clients
from app.controller.common import (
    error_handler,
    load_config,
    check_xray_config,
    check_root,
    get_vless_inbound,
    save_config,
    stdout_console,
    get_runtime_stats,
    get_stored_stats,
    print_error,
)
from app.controller.completions import complete_client_name
from app.controller.data import ClientData, RuleData
from app.defaults import (
    XRAY_CONFIG_PATH,
    STYLE_ACCENT_NEUTRAL,
    STYLE_REGULAR,
    STYLE_WARN,
    STYLE_ACCENT_UP,
    STYLE_ACCENT_DOWN,
    EXIT_CLIENTS_ERROR,
    DISABLED_CLIENTS_RULE_NAME,
    DISABLED_CLIENTS_RULE_PRIORITY,
)
from app.model.routing import Rule, Routing
from app.model.xray import Xray
from app.model.veepeenet import VeePeeNetStats
from app.utils import (
    get_new_items,
    get_vless_client_url,
    remove_duplicates,
    get_existing_items,
)
from app.view import ClientsView, ClientView, TrafficStatsView


@clients.command(help='Register clients to service')
@error_handler(default_message='Error adding clients to service', default_code=EXIT_CLIENTS_ERROR)
def add(client_names: Annotated[list[str],
        Argument(help='List of new client of server')],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()
    _add_clients(client_names)


@clients.command(help='Remove clients from service')
@error_handler(default_message='Error removing clients from service',
               default_code=EXIT_CLIENTS_ERROR)
def remove(client_names: Annotated[list[str],
        Argument(help='List of clients to remove from Xray Vless Reality server',
                 autocompletion=complete_client_name)],
           _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()
    _remove_clients(client_names)


@clients.command(help='List clients of service', name='list')
@error_handler(default_message='Error listing clients of service', default_code=EXIT_CLIENTS_ERROR)
def show(
        json: Annotated[bool, Option(help='Show JSON formatted info')] = False,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_xray_config()
    xray_config = load_config(XRAY_CONFIG_PATH)
    display_stats = get_stored_stats()
    display_stats += get_runtime_stats()

    view = get_clients_view(xray_config, display_stats)
    if json:
        stdout_console.print_json(view.model_dump_json(exclude_none=True), indent=2)
    else:
        url_console = Console(soft_wrap=True, width=2**15)
        url_console.print(view.rich_repr())


@clients.callback(invoke_without_command=True)
def show_default(
        ctx: Context,
        json: Annotated[bool, Option(help='Show JSON formatted info')] = False,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    if ctx.invoked_subcommand is None:
        show(json=json, _debug=_debug)


@clients.command(help='Disable clients access to service')
@error_handler(default_message='Error disabling clients access', default_code=EXIT_CLIENTS_ERROR)
def disable(client_names: Annotated[list[str],
            Argument(help='List of clients to disable', autocompletion=complete_client_name)],
            _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()
    _set_clients_disabled_state(client_names, disabled=True)


@clients.command(help='Enable clients access to service')
@error_handler(default_message='Error enabling clients access', default_code=EXIT_CLIENTS_ERROR)
def enable(client_names: Annotated[list[str],
           Argument(help='List of clients to enable', autocompletion=complete_client_name)],
           _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()
    _set_clients_disabled_state(client_names, disabled=False)


def get_clients_view(xray_config: Xray, stats: VeePeeNetStats | None = None) -> ClientsView:
    inbound = get_vless_inbound(xray_config)
    disabled_emails = _get_disabled_emails(xray_config)

    clients_data = [ClientData.from_model(client, i)
                    for i, client in enumerate(inbound.settings.clients or [])]
    clients_views: list[ClientView] = []
    for client_data in clients_data:
        client_ts = stats.client.get(client_data.name) if stats else None
        client_email = client_data.to_model().email
        clients_views.append(ClientView(
            name=client_data.name,
            url=get_vless_client_url(client_data.name, xray_config) or 'error',
            disabled=client_email in disabled_emails,
            stats=TrafficStatsView(
                uplink=client_ts.uplink, downlink=client_ts.downlink) if client_ts else TrafficStatsView()))
    return ClientsView(clients=clients_views)


def _get_disabled_emails(xray_config: Xray) -> set[str]:
    rules = xray_config.routing.rules if xray_config.routing and xray_config.routing.rules else []
    for index, rule in enumerate(rules):
        rule_data = RuleData.from_model(rule, index)
        if (rule_data.name == DISABLED_CLIENTS_RULE_NAME
                and rule_data.priority == DISABLED_CLIENTS_RULE_PRIORITY):
            return set(rule_data.users or [])
    return set()


def _update_disabled_rule(xray_config: Xray, disabled_emails: set[str]) -> None:
    existing_rules = xray_config.routing.rules if xray_config.routing and xray_config.routing.rules else []
    updated_rules: list[Rule] = []

    for index, rule in enumerate(existing_rules):
        rule_data = RuleData.from_model(rule, index)
        if (rule_data.name == DISABLED_CLIENTS_RULE_NAME
                and rule_data.priority == DISABLED_CLIENTS_RULE_PRIORITY):
            continue
        updated_rules.append(rule)

    if disabled_emails:
        updated_rules.append(Rule(
            tag=f'{DISABLED_CLIENTS_RULE_NAME}.{DISABLED_CLIENTS_RULE_PRIORITY}',
            outbound_tag='blackhole',
            user=sorted(disabled_emails),
        ))

    updated_rules.sort(key=lambda rule: RuleData.from_model(rule, 0).priority)
    if xray_config.routing is None:
        xray_config.routing = Routing()
    xray_config.routing.rules = updated_rules or None


def _get_client_emails_by_name(xray_config: Xray) -> dict[str, str]:
    inbound = get_vless_inbound(xray_config)
    clients_data = [ClientData.from_model(client, i)
                    for i, client in enumerate(inbound.settings.clients or [])]
    return {
        client_data.name: client_data.to_model().email 
        for client_data in clients_data
    } # type: ignore


def _split_client_names_by_disabled_state(
        names: list[str],
        name_to_email: dict[str, str],
        disabled_emails: set[str],
        disabled: bool) -> tuple[list[str], list[str]]:
    unchanged_names: list[str] = []
    changed_names: list[str] = []

    for name in names:
        is_disabled = name_to_email[name] in disabled_emails
        if is_disabled == disabled:
            unchanged_names.append(name)
        else:
            changed_names.append(name)

    return unchanged_names, changed_names


def _set_clients_disabled_state(
        names: list[str],
        disabled: bool,
        xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    xray_config = load_config(xray_config_path)
    name_to_email = _get_client_emails_by_name(xray_config)
    unique_names = remove_duplicates(names)
    unknown_names = get_new_items(list(name_to_email), unique_names)
    if unknown_names:
        unknown_names_rich = Text(', ', STYLE_REGULAR).join(
            [Text(name, STYLE_ACCENT_NEUTRAL) for name in unknown_names])
        print_error(Text.assemble(
            ('Unknown clients: ', STYLE_REGULAR),
            unknown_names_rich,
        ))
        raise Exit(code=EXIT_CLIENTS_ERROR)

    disabled_emails = _get_disabled_emails(xray_config)
    target_emails = {name_to_email[name] for name in unique_names}
    unchanged_names, changed_names = _split_client_names_by_disabled_state(
        unique_names, name_to_email, disabled_emails, disabled)

    if unchanged_names:
        unchanged_names_rich = Text(', ', STYLE_REGULAR).join(
            [Text(name, STYLE_ACCENT_NEUTRAL) for name in unchanged_names])
        stdout_console.print(Text.assemble(
            ('These clients are already ', STYLE_REGULAR),
            ('disabled', STYLE_WARN) if disabled else ('enabled', STYLE_ACCENT_UP),
            (': ', STYLE_REGULAR),
            unchanged_names_rich,
        ))

    if not changed_names:
        stdout_console.print(Text(
            'No new clients to disable' if disabled else 'No clients to enable',
            STYLE_WARN,
        ))
        return

    if disabled:
        disabled_emails.update(target_emails)
    else:
        disabled_emails.difference_update(target_emails)

    _update_disabled_rule(xray_config, disabled_emails)
    save_config(xray_config, xray_config_path)

    changed_names_rich = Text(', ', STYLE_REGULAR).join(
        [Text(name, STYLE_ACCENT_DOWN if disabled else STYLE_ACCENT_UP) for name in changed_names])
    stdout_console.print(Text.assemble(
        ('Disabled clients: ', STYLE_REGULAR) if disabled else ('Enabled clients: ', STYLE_REGULAR),
        changed_names_rich,
    ))


def _add_clients(names: list[str], xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    xray_config = load_config(xray_config_path)
    inbound = get_vless_inbound(xray_config)
    reality_settings = inbound.stream_settings.reality_settings
    namespace = UUID(xray_config.veepeenet and xray_config.veepeenet.namespace)

    existing_clients_data = [ClientData.from_model(client, i)
                             for i, client in enumerate(inbound.settings.clients or [])]
    existing_names = [client_data.name for client_data in existing_clients_data]
    new_names = get_new_items(existing_names, remove_duplicates(names))
    already_existing_names = get_existing_items(existing_names, names)

    if already_existing_names:
        skipped_names = Text(', ', STYLE_REGULAR).join(
            [Text(name, STYLE_ACCENT_NEUTRAL) for name in already_existing_names])
        stdout_console.print(Text.assemble(
            ('These clients ', STYLE_REGULAR),
            ('already exist ', STYLE_WARN),
            ('and will be skipped: ', STYLE_REGULAR),
            skipped_names
        ))
    if not new_names:
        stdout_console.print(Text('No new clients found', STYLE_WARN))
        return

    existing_short_ids = [client_data.short_id for client_data in existing_clients_data]
    for name in new_names:
        data = ClientData(name=name, namespace=namespace)
        existing_short_ids.append(data.short_id)
        existing_clients_data.append(data)

    inbound.settings.clients = [client_data.to_model() for client_data in existing_clients_data]
    reality_settings.short_ids = existing_short_ids

    save_config(xray_config, xray_config_path)
    added_names = Text(', ', STYLE_REGULAR).join(
        [Text(name, STYLE_ACCENT_UP) for name in new_names])
    stdout_console.print(Text('Added new clients: ', STYLE_REGULAR).append(added_names))


def _remove_clients(names: list[str], xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    xray_config = load_config(xray_config_path)
    inbound = get_vless_inbound(xray_config)
    existing_clients = inbound.settings.clients
    reality_settings = inbound.stream_settings.reality_settings

    existing_clients_data = [ClientData.from_model(client, i)
                             for i, client in enumerate(existing_clients or [])]
    existing_names = [client_data.name for client_data in existing_clients_data]
    removable_names = get_existing_items(existing_names, remove_duplicates(names))
    unknown_names = get_new_items(existing_names, names)

    if unknown_names:
        unknown_names_rich = Text(', ', STYLE_REGULAR).join(
            [Text(name, STYLE_ACCENT_NEUTRAL) for name in unknown_names])
        stdout_console.print(
            Text.assemble(
                ('These clients ', STYLE_REGULAR),
                ('are unknown', STYLE_WARN),
                (' and will be skipped: ', STYLE_REGULAR),
                unknown_names_rich)
        )
    if not removable_names:
        stdout_console.print(Text('No removable clients found', STYLE_WARN))
        return

    remaining_clients_data = [cd for cd in existing_clients_data if cd.name not in removable_names]
    inbound.settings.clients = [client_data.to_model() for client_data in remaining_clients_data]
    reality_settings.short_ids = [cd.short_id for cd in remaining_clients_data]
    disabled_emails = _get_disabled_emails(xray_config)
    remaining_emails = {client_data.to_model().email for client_data in remaining_clients_data}
    _update_disabled_rule(xray_config, disabled_emails & remaining_emails)

    save_config(xray_config, xray_config_path)
    removed_names = Text(', ', STYLE_REGULAR).join(
        [Text(name, STYLE_ACCENT_DOWN) for name in removable_names])
    stdout_console.print(Text('Removed clients: ', STYLE_REGULAR).append(removed_names))
