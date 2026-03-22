from pathlib import Path
from typing import Annotated
from uuid import UUID

from rich.console import Console
from rich.text import Text
from typer import Argument, Option
from xxhash import xxh64

from app.cli import clients
from app.controller.common import (
    error_handler,
    load_config,
    check_xray_config,
    check_root,
    get_vless_inbound,
    stdout_console,
    save_config,
    ClientData,
)
from app.controller.completions import complete_client_name
from app.defaults import (
    XRAY_CONFIG_PATH,
    STYLE_ACCENT_NEUTRAL,
    STYLE_REGULAR,
    STYLE_WARN,
    STYLE_ACCENT_UP,
    STYLE_ACCENT_DOWN,
    EXIT_CLIENTS_ERROR,
)
from app.utils import (
    get_new_items,
    get_vless_client_url,
    remove_duplicates,
    get_existing_items,
)
from app.view import ClientsView, ClientView


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
        Argument(help='List of clients to remove from Xray VLESS Reality server',
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
    inbound = get_vless_inbound(xray_config)
    host = xray_config.veepeenet.host

    clients_data = [ClientData.from_model(client, host) for client in inbound.settings.clients]
    clients_views = [ClientView(
        name=client_data.name,
        url=get_vless_client_url(client_data.name, xray_config))
                     for client_data in clients_data]
    view = ClientsView(clients=clients_views)

    if json:
        stdout_console.print_json(view.model_dump_json(exclude_none=True), indent=2)
    else:
        url_console = Console(soft_wrap=True, width=2**15)
        url_console.print(view.rich_repr())


def _add_clients(names: list[str], xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    xray_config = load_config(xray_config_path)
    inbound = get_vless_inbound(xray_config)
    reality_settings = inbound.stream_settings.reality_settings
    namespace = UUID(xray_config.veepeenet.namespace)

    existing_clients_data = [ClientData.from_model(client, xray_config.veepeenet.host)
                             for client in inbound.settings.clients]
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
        short_id = xxh64(name).hexdigest()
        existing_short_ids.append(short_id)
        existing_clients_data.append(ClientData(
            name=name, short_id=short_id, host=xray_config.veepeenet.host, namespace=namespace))

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
    host = xray_config.veepeenet.host
    reality_settings = inbound.stream_settings.reality_settings

    existing_clients_data = [ClientData.from_model(client, host) for client in existing_clients]
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

    save_config(xray_config, xray_config_path)
    removed_names = Text(', ', STYLE_REGULAR).join(
        [Text(name, STYLE_ACCENT_DOWN) for name in removable_names])
    stdout_console.print(Text('Removed clients: ', STYLE_REGULAR).append(removed_names))
