from re import fullmatch
from typing import Annotated, Literal, get_args

from rich.text import Text
from typer import Option, Argument, Exit

from app.cli import routing
from app.controller.common import RuleData
from app.controller.common import (
    error_handler,
    load_config,
    check_xray_config,
    check_root,
    get_vless_inbound,
    stdout_console,
    print_error
)
from app.controller.completions import complete_route_name, complete_outbound_name
from app.defaults import (
    XRAY_CONFIG_PATH,
    GEO_IP_URL,
    GEO_SITE_URL,
    XRAY_GEO_IP_DATA_PATH,
    XRAY_GEO_SITE_DATA_PATH,
)
from app.model.routing import Routing
from app.model.types import RuleProtocolType, RoutingDomainStrategyType
from app.model.xray import Xray
from app.utils import write_text_file, install_geo_data
from app.view import RoutingView, RuleView


@routing.command(help='Show routing settings', name='list')
@error_handler(default_message='Error showing routing settings', default_code=50)
def show(
        json: Annotated[bool, Option(help='Show JSON formatted info')] = False,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    xray_config = _init_and_load_config()

    view: RoutingView
    if xray_config.routing is None:
        view = RoutingView()
    else:
        domain_strategy = _get_domain_strategy(xray_config)
        rules_view: list[RuleView] = []
        for i, rule in enumerate(xray_config.routing.rules):
            rule_data = RuleData.from_model(rule, i)
            rule_view = RuleView(
                name=rule_data.name,
                domains=rule_data.domains,
                ips=rule_data.ips,
                ports=rule_data.ports,
                protocols=rule_data.protocols,
                outbound_name=rule_data.outbound_name,
                priority=rule_data.priority
            )
            rules_view.append(rule_view)
        view = RoutingView(domain_strategy=domain_strategy, rules=rules_view)

    if json:
        stdout_console.print_json(view.model_dump_json(exclude_none=True, indent=2))
    else:
        stdout_console.print(view.rich_repr())


@routing.command(help='Add rule to service')
@error_handler(default_message='Error adding rule to service', default_code=50)
def add_rule(
        name: Annotated[str, Argument(help='Rule name')],
        outbound: Annotated[
            str,
            Option(help='Outbound name to which the rule will direct traffic',
                   autocompletion=complete_outbound_name)],
        domain: Annotated[
            list[str],
            Option(help='List of domain patterns to match (e.g. "domain:example.com")')] = None,
        ip: Annotated[
            list[str],
            Option(help='List of IPs or IP ranges to match (e.g. "123.123.123.123')] = None,
        ports: Annotated[
            str,
            Option(help='Port or port range to match (e.g. "53,443,60-89", "1000-2000")')] = None,
        protocol: Annotated[
            list[str],
            Option(help='List of protocols to match: http, tls, quic or bittorrent')] = None,
        priority: Annotated[
            int,
            Option(
                help='Priority of the rule (lower value means higher priority)')] = None,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    xray_config = _init_and_load_config()

    if not _is_outbound_exists(xray_config, outbound):
        print_error(Text.assemble('Outbound ', (outbound, 'bold yellow'), ' not found'))
        raise Exit(code=51)
    if not (domain or ip or ports or protocol):
        print_error(
            'At least one condition (domain, ip, ports, protocol) must be specified')
        raise Exit(code=52)
    if not _is_correct_protocols(protocol):
        allowed_protocols = ', '.join(get_args(RuleProtocolType))
        print_error(
            f'Invalid protocols: {",".join(protocol)}. Allowed values: {allowed_protocols}')
        raise Exit(code=53)
    if not _is_correct_ports_format(ports):
        print_error(f'Invalid ports format: "{ports}"')
        raise Exit(code=54)

    all_rules = _get_existing_rules(xray_config)
    if _find_rule_by_name(all_rules, name):
        print_error(Text.assemble(
            'Rule ', (f'{name}', 'bold yellow'), ' already exists'
        ))
        raise Exit(code=55)

    new_rule = RuleData(name=name, outbound_name=outbound, protocols=protocol,
                        ports=ports, domains=domain, ips=ip,
                        priority=priority or (len(all_rules) + 1) * 10)
    all_rules.append(new_rule)

    _save_rules(xray_config, all_rules)
    stdout_console.print(Text.assemble(
        'Rule ',
        (f'{name} --> {outbound}', 'bold green'),
        ' successfully added'))


@routing.command(help='Remove rule from service')
@error_handler(default_message='Error removing rule from service', default_code=50)
def remove_rule(
        name: Annotated[str, Argument(help='Rule name', autocompletion=complete_route_name)],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    xray_config = _init_and_load_config()

    all_rules = _get_existing_rules(xray_config)
    rule_to_delete = _find_rule_by_name(all_rules, name)

    if rule_to_delete is None:
        print_error(
            Text.assemble('Rule ', (f'{name}', 'bold yellow'), ' not found'))
        raise Exit(code=56)

    all_rules.remove(rule_to_delete)

    _save_rules(xray_config, all_rules)
    stdout_console.print(
        Text.assemble('Rule ', (f'{name}', 'bold red'), ' successfully removed'))


@routing.command(help='Rename rule')
@error_handler()
def rename_rule(
        name: Annotated[str, Argument(
            help='Current rule name', autocompletion=complete_route_name)],
        new_name: Annotated[str, Option(help='New rule name')],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    xray_config = _init_and_load_config()

    all_rules = _get_existing_rules(xray_config)
    rule_to_rename = _find_rule_by_name(all_rules, name)

    if rule_to_rename is None:
        print_error(
            Text.assemble('Rule ', (f'{name}', 'bold yellow'), ' not found'))
        raise Exit(code=56)

    rule_to_rename.name = new_name

    _save_rules(xray_config, all_rules)
    stdout_console.print(
        Text.assemble(
        'Rule ',
            (f'{name}', 'bold green'),
            ' successfully renamed to ',
            (f'{new_name}', 'bold green')))


@routing.command(help='Change rule priority', name='set-priority')
@error_handler(default_message='Error changing rule priority', default_code=50)
def set_rule_priority(
        name: Annotated[str, Argument(help='Rule name', autocompletion=complete_route_name)],
        priority: Annotated[int, Option(help='New priority value (lower = higher priority)')],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    xray_config = _init_and_load_config()

    all_rules = _get_existing_rules(xray_config)
    rule_to_update = _find_rule_by_name(all_rules, name)

    if rule_to_update is None:
        print_error(
            Text.assemble('Rule ', (f'{name}', 'bold yellow'), ' not found'))
        raise Exit(code=56)

    if rule_to_update.priority == priority:
        print_error(Text.assemble(
            'Rule ', (f'{name}', 'bold yellow'), f' already has priority {priority}'
        ))
        raise Exit(code=57)
    rule_to_update.priority = priority

    _save_rules(xray_config, all_rules)
    stdout_console.print(Text.assemble(
        'Rule ', (f'{name}', 'bold green'), f' priority successfully changed to {priority}'
    ))


@routing.command(help='Change rule conditions')
@error_handler(default_message='Error changing rule conditions', default_code=50)
def change_rule(
        name: Annotated[str, Argument(help='Rule name', autocompletion=complete_route_name)],
        action: Annotated[
            Literal['put', 'del'],
            Argument(help='Change type: "put" - add new values, "del" - delete values')
        ],
        domain: Annotated[
            list[str],
            Option(help='List of domain patterns to match (e.g. "domain:example.com")')] = None,
        ip: Annotated[
            list[str],
            Option(help='List of IPs or IP ranges to match (e.g. "')] = None,
        ports: Annotated[
            str,
            Option(help='Port or port range to match (e.g. "53", "1000-2000")')] = None,
        protocol: Annotated[
            list[str],
            Option(help='List of protocols to match: http, tls, quic or bittorrent')] = None,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    xray_config = _init_and_load_config()

    if not (domain or ip or ports or protocol):
        print_error(
            'At least one condition (domain, ip, ports, protocol) must be specified')
        raise Exit(code=52)
    if not _is_correct_protocols(protocol):
        allowed_protocols = ', '.join(get_args(RuleProtocolType))
        print_error(
            f'Invalid protocols: {",".join(protocol)}. Allowed values: {allowed_protocols}')
        raise Exit(code=53)
    if ports and not _is_correct_ports_format(ports):
        print_error(f'Invalid ports format: "{ports}"')
        raise Exit(code=54)

    all_rules = _get_existing_rules(xray_config)
    rule_to_change = _find_rule_by_name(all_rules, name)

    if rule_to_change is None:
        print_error(Text.assemble('Rule ', (f'{name}', 'bold yellow'), ' not found'))
        raise Exit(code=56)

    if action == 'put':
        _add_conditions(rule_to_change, domain, ip, ports, protocol)
    else:
        _remove_conditions(rule_to_change, domain, ip, ports, protocol)

    _save_rules(xray_config, all_rules)
    stdout_console.print(Text.assemble('Rule ', (f'{name}', 'bold green'), ' changed'))


@routing.command(help='Set domain strategy')
@error_handler(default_message='Error setting domain strategy', default_code=50)
def set_domain_strategy(
        strategy: Annotated[RoutingDomainStrategyType, Argument(help='domain strategy value')],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    xray_config = _init_and_load_config()

    if not xray_config.routing or not xray_config.routing.rules:
        print_error('At least one rule must be defined to set domain strategy')
        raise Exit(code=58)

    current_strategy = _get_domain_strategy(xray_config)
    if current_strategy == strategy:
        print_error(Text.assemble(
            'Domain strategy is already set to ', (f'{strategy}', 'bold yellow')
        ))
        raise Exit(code=59)

    xray_config.routing.domain_strategy = strategy
    write_text_file(
        XRAY_CONFIG_PATH,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    stdout_console.print(Text.assemble(
        'Domain strategy successfully changed to ', (f'{strategy}', 'bold green')
    ))


@routing.command(help='Change rule outbound', name='change-outbound')
@error_handler(default_message='Error changing rule outbound', default_code=50)
def change_outbound(
        name: Annotated[str, Argument(help='Rule name', autocompletion=complete_route_name)],
        outbound: Annotated[
            str,
            Option(help='New outbound name',
                   autocompletion=complete_outbound_name)],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    xray_config = _init_and_load_config()

    all_rules = _get_existing_rules(xray_config)
    rule_to_change = _find_rule_by_name(all_rules, name)

    if rule_to_change is None:
        print_error(Text.assemble('Rule ', (f'{name}', 'bold yellow'), ' not found'))
        raise Exit(code=56)

    if not _is_outbound_exists(xray_config, outbound):
        print_error(Text.assemble('Outbound ', (outbound, 'bold yellow'), ' not found'))
        raise Exit(code=51)

    if rule_to_change.outbound_name == outbound:
        print_error(Text.assemble(
            'Rule ', (f'{name}', 'bold yellow'),
            ' already uses outbound ', (outbound, 'bold yellow')))
        raise Exit(code=57)

    rule_to_change.outbound_name = outbound

    _save_rules(xray_config, all_rules)
    stdout_console.print(Text.assemble(
        'Rule ', (f'{name}', 'bold green'),
        ' outbound changed to ', (outbound, 'bold green')))


def _is_outbound_exists(xray_config: Xray, outbound_name: str) -> bool:
    for outbound in xray_config.outbounds:
        if outbound.tag == outbound_name:
            return True
    return False

def _is_correct_ports_format(ports: str) -> bool:
    if not ports:
        return True
    return fullmatch(r'\d{1,5}(?:-\d{1,5})?(?:,\d{1,5}(?:-\d{1,5})?)*', ports) is not None

def _is_correct_protocols(protocols: list[str]) -> bool:
    if not protocols:
        return True
    return all(protocol in get_args(RuleProtocolType) for protocol in protocols)

def _get_domain_strategy(xray_config: Xray) -> RoutingDomainStrategyType:
    if xray_config.routing and xray_config.routing.domain_strategy:
        return xray_config.routing.domain_strategy
    return 'AsIs'

def _get_existing_rules(xray_config: Xray) -> list[RuleData]:
    if xray_config.routing is None:
        return []
    return [RuleData.from_model(rule, i) for i, rule in enumerate(xray_config.routing.rules)]


def _init_and_load_config() -> Xray:
    check_xray_config()
    return load_config(XRAY_CONFIG_PATH)


def _find_rule_by_name(rules: list[RuleData], name: str) -> RuleData | None:
    for rule in rules:
        if rule.name == name:
            return rule
    return None


def _save_rules(xray_config: Xray, rules: list[RuleData] | None = None) -> None:
    if rules:
        rules.sort(key=lambda x: x.priority)
        model_rules = [rule.to_model() for rule in rules]

        if xray_config.routing is None:
            xray_config.routing = Routing()
        xray_config.routing.rules = model_rules
        get_vless_inbound(xray_config).sniffing.enabled = True

        all_geo_ip_rules = [ip
                             for rule in rules if rule.ips
                             for ip in rule.ips
                             if ip.startswith('geoip:')]
        all_geo_site_rules = [domain
                              for rule in rules if rule.domains
                              for domain in rule.domains
                              if domain.startswith('geosite:')]

        if all_geo_ip_rules and not XRAY_GEO_IP_DATA_PATH.exists():
            with stdout_console.status('Installing GeoIP data'):
                install_geo_data(GEO_IP_URL, XRAY_GEO_IP_DATA_PATH)
            stdout_console.print('GeoIP data installed')
        if all_geo_site_rules and not XRAY_GEO_SITE_DATA_PATH.exists():
            with stdout_console.status('Installing Geosite data'):
                install_geo_data(GEO_SITE_URL, XRAY_GEO_SITE_DATA_PATH)
            stdout_console.print('Geosite data installed')
    else:
        xray_config.routing = None
        get_vless_inbound(xray_config).sniffing.enabled = False

    write_text_file(
        XRAY_CONFIG_PATH,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)


def _add_conditions(
        rule: RuleData,
        domains: list[str] | None,
        ips: list[str] | None,
        ports: str | None,
        protocols: list[RuleProtocolType] | None
) -> None:
    if domains:
        rule.domains = _add_unique_items(rule.domains or [], domains)
    if ips:
        rule.ips = _add_unique_items(rule.ips or [], ips)
    if ports:
        rule.ports = _merge_ports(rule.ports, ports)
    if protocols:
        rule.protocols = _add_unique_items(rule.protocols or [], protocols)


def _remove_conditions(
        rule: RuleData,
        domains: list[str] | None,
        ips: list[str] | None,
        ports: str | None,
        protocols: list[RuleProtocolType] | None
) -> None:
    if domains and rule.domains:
        rule.domains = [d for d in rule.domains if d not in domains]
        rule.domains = rule.domains if rule.domains else None
    if ips and rule.ips:
        rule.ips = [ip for ip in rule.ips if ip not in ips]
        rule.ips = rule.ips if rule.ips else None
    if ports and rule.ports:
        rule.ports = _subtract_ports(rule.ports, ports)
    if protocols and rule.protocols:
        rule.protocols = [p for p in rule.protocols if p not in protocols]
        rule.protocols = rule.protocols if rule.protocols else None


def _merge_ports(current: str | None, new: str) -> str:
    if not current:
        return new
    current_list = current.split(',')
    new_list = new.split(',')
    merged = _add_unique_items(current_list, new_list)
    return ','.join(sorted(merged, key=lambda x: int(x.split('-')[0])))


def _subtract_ports(current: str, to_remove: str) -> str | None:
    current_list = current.split(',')
    remove_set = set(to_remove.split(','))
    result = [port for port in current_list if port not in remove_set]
    return ','.join(sorted(result, key=lambda x: int(x.split('-')[0]))) if result else None


def _add_unique_items(existing: list, new_items: list) -> list:
    existing_set = set(existing)
    result = list(existing)
    for item in new_items:
        if item not in existing_set:
            result.append(item)
            existing_set.add(item)
    return result
