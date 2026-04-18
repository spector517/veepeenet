from re import fullmatch
from typing import Annotated, Literal, Any, get_args

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
    print_error,
    save_config,
    stdout_console,
)
from app.controller.completions import complete_route_name, complete_outbound_name
from app.defaults import (
    XRAY_CONFIG_PATH,
    GEO_IP_URL,
    GEO_SITE_URL,
    XRAY_GEO_IP_DATA_PATH,
    XRAY_GEO_SITE_DATA_PATH,
    STYLE_REGULAR,
    STYLE_OK,
    STYLE_ACCENT_UP,
    STYLE_ACCENT_DOWN,
    STYLE_ACCENT_NEUTRAL,
    STYLE_VALUE,
    EXIT_ROUTING_ERROR,
    EXIT_ROUTING_OUTBOUND_NOT_FOUND,
    EXIT_ROUTING_NO_CONDITIONS,
    EXIT_ROUTING_INVALID_PROTOCOLS,
    EXIT_ROUTING_INVALID_PORTS,
    EXIT_ROUTING_RULE_EXISTS,
    EXIT_ROUTING_RULE_NOT_FOUND,
    EXIT_ROUTING_RULE_SAME_VALUE,
    EXIT_ROUTING_NO_RULES,
    EXIT_ROUTING_STRATEGY_SAME,
)
from app.model.routing import Routing
from app.model.types import RuleProtocolType, RoutingDomainStrategyType
from app.model.xray import Xray
from app.utils import install_geo_data
from app.view import RoutingView, RuleView


@routing.command(help='Show routing settings', name='list')
@error_handler(default_message='Error showing routing settings', default_code=EXIT_ROUTING_ERROR)
def show(
        json: Annotated[bool, Option(help='Show JSON formatted info')] = False,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    xray_config = _init_and_load_config()
    view = get_routing_view(xray_config)

    if json:
        stdout_console.print_json(view.model_dump_json(exclude_none=True, indent=2))
    else:
        stdout_console.print(view.rich_repr())


def get_routing_view(xray_config: Xray) -> RoutingView:
    if xray_config.routing is None:
        return RoutingView()
    domain_strategy = _get_domain_strategy(xray_config)
    rules_view: list[RuleView] = []
    if xray_config.routing and xray_config.routing.rules:
        rules = xray_config.routing.rules
    else:
        rules = []
    for i, rule in enumerate(rules):
        rule_data = RuleData.from_model(rule, i)
        rule_view = RuleView(
            name=rule_data.name,
            domains=rule_data.domains,
            ips=rule_data.ips,
            ports=rule_data.ports,
            protocols=rule_data.protocols, # pyright: ignore[reportArgumentType]
            outbound_name=rule_data.outbound_name,
            priority=rule_data.priority
        )
        rules_view.append(rule_view)
    return RoutingView(domain_strategy=domain_strategy, rules=rules_view)


@routing.command(help='Add rule to service')
@error_handler(default_message='Error adding rule to service', default_code=EXIT_ROUTING_ERROR)
def add_rule(
        name: Annotated[str, Argument(help='Rule name')],
        outbound: Annotated[
            str,
            Option(help='Outbound name to which the rule will direct traffic',
                   autocompletion=complete_outbound_name)],
        domain: Annotated[
            list[str] | None,
            Option(help='List of domain patterns to match (e.g. "domain:example.com")')] = None,
        ip: Annotated[
            list[str] | None,
            Option(help='List of IPs or IP ranges to match (e.g. "123.123.123.123')] = None,
        ports: Annotated[
            str | None,
            Option(help='Port or port range to match (e.g. "53,443,60-89", "1000-2000")')] = None,
        protocol: Annotated[
            list[str] | None,
            Option(help='List of protocols to match: http, tls, quic or bittorrent')] = None,
        priority: Annotated[
            int | None,
            Option(
                help='Priority of the rule (lower value means higher priority)')] = None,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    xray_config = _init_and_load_config()

    if not _is_outbound_exists(xray_config, outbound):
        print_error(Text.assemble(
            ('Outbound ', STYLE_REGULAR),
            (outbound, STYLE_ACCENT_NEUTRAL),
            (' not found', STYLE_REGULAR)))
        raise Exit(code=EXIT_ROUTING_OUTBOUND_NOT_FOUND)

    if not (domain or ip or ports or protocol):
        print_error(Text(
            'At least one condition (domain, ip, ports, protocol) must be specified',
            STYLE_REGULAR))
        raise Exit(code=EXIT_ROUTING_NO_CONDITIONS)

    if protocol and not _is_correct_protocols(protocol):
        allowed_protocols = ', '.join(get_args(RuleProtocolType))
        print_error(Text.assemble(
            ('Invalid protocols: ', STYLE_REGULAR),
            (','.join(protocol), STYLE_ACCENT_NEUTRAL),
            ('. Allowed values: ', STYLE_REGULAR),
            (allowed_protocols, STYLE_VALUE)))
        raise Exit(code=EXIT_ROUTING_INVALID_PROTOCOLS)

    if ports and not _is_correct_ports_format(ports):
        print_error(Text.assemble(
            ('Invalid ports format: ', STYLE_REGULAR),
            (ports, STYLE_ACCENT_NEUTRAL)))
        raise Exit(code=EXIT_ROUTING_INVALID_PORTS)

    all_rules = _get_existing_rules(xray_config)
    if _find_rule_by_name(all_rules, name):
        print_error(Text.assemble(
            ('Rule ', STYLE_REGULAR),
            (name, STYLE_ACCENT_NEUTRAL),
            (' already exists', STYLE_REGULAR)))
        raise Exit(code=EXIT_ROUTING_RULE_EXISTS)

    new_rule = RuleData(name=name, outbound_name=outbound,
                        protocols=protocol, # pyright: ignore[reportArgumentType]
                        ports=ports, domains=domain, ips=ip,
                        priority=priority or (len(all_rules) + 1) * 10)
    all_rules.append(new_rule)

    _save_rules(xray_config, all_rules)
    stdout_console.print(Text.assemble(
        ('Rule ', STYLE_REGULAR),
        (name, STYLE_ACCENT_UP),
        (' --> ', STYLE_ACCENT_NEUTRAL),
        (outbound, STYLE_VALUE),
        (' successfully added', STYLE_REGULAR)))


@routing.command(help='Remove rule from service')
@error_handler(default_message='Error removing rule from service', default_code=EXIT_ROUTING_ERROR)
def remove_rule(
        name: Annotated[str, Argument(help='Rule name', autocompletion=complete_route_name)],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    xray_config = _init_and_load_config()

    all_rules = _get_existing_rules(xray_config)
    rule_to_delete = _find_rule_by_name(all_rules, name)

    if rule_to_delete is None:
        print_error(Text.assemble(
            ('Rule ', STYLE_REGULAR),
            (name, STYLE_ACCENT_NEUTRAL),
            (' not found', STYLE_REGULAR)))
        raise Exit(code=EXIT_ROUTING_RULE_NOT_FOUND)

    all_rules.remove(rule_to_delete)

    _save_rules(xray_config, all_rules)
    stdout_console.print(Text.assemble(
        ('Rule ', STYLE_REGULAR),
        (name, STYLE_ACCENT_DOWN),
        (' successfully removed', STYLE_REGULAR)))


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
        print_error(Text.assemble(
            ('Rule ', STYLE_REGULAR),
            (name, STYLE_ACCENT_NEUTRAL),
            (' not found', STYLE_REGULAR)))
        raise Exit(code=EXIT_ROUTING_RULE_NOT_FOUND)

    rule_to_rename.name = new_name

    _save_rules(xray_config, all_rules)
    stdout_console.print(Text.assemble(
        ('Rule ', STYLE_REGULAR),
        (name, STYLE_ACCENT_NEUTRAL),
        (' successfully renamed to ', STYLE_REGULAR),
        (new_name, STYLE_ACCENT_UP)))


@routing.command(help='Change rule priority', name='set-priority')
@error_handler(default_message='Error changing rule priority', default_code=EXIT_ROUTING_ERROR)
def set_rule_priority(
        name: Annotated[str, Argument(help='Rule name', autocompletion=complete_route_name)],
        priority: Annotated[int, Option(help='New priority value (lower = higher priority)')],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    xray_config = _init_and_load_config()

    all_rules = _get_existing_rules(xray_config)
    rule_to_update = _find_rule_by_name(all_rules, name)

    if rule_to_update is None:
        print_error(Text.assemble(
            ('Rule ', STYLE_REGULAR),
            (name, STYLE_ACCENT_NEUTRAL),
            (' not found', STYLE_REGULAR)))
        raise Exit(code=EXIT_ROUTING_RULE_NOT_FOUND)

    if rule_to_update.priority == priority:
        print_error(Text.assemble(
            ('Rule ', STYLE_REGULAR),
            (name, STYLE_ACCENT_NEUTRAL),
            (' already has priority ', STYLE_REGULAR),
            (str(priority), STYLE_VALUE)))
        raise Exit(code=EXIT_ROUTING_RULE_SAME_VALUE)
    rule_to_update.priority = priority

    _save_rules(xray_config, all_rules)
    stdout_console.print(Text.assemble(
        ('Rule ', STYLE_REGULAR),
        (name, STYLE_ACCENT_UP),
        (' priority successfully changed to ', STYLE_REGULAR),
        (str(priority), STYLE_VALUE)))


@routing.command(help='Change rule conditions')
@error_handler(default_message='Error changing rule conditions', default_code=EXIT_ROUTING_ERROR)
def change_rule(
        name: Annotated[str, Argument(help='Rule name', autocompletion=complete_route_name)],
        action: Annotated[
            Literal['put', 'del'],
            Argument(help='Change type: "put" - add new values, "del" - delete values')
        ],
        domain: Annotated[
            list[str] | None,
            Option(help='List of domain patterns to match (e.g. "domain:example.com")')] = None,
        ip: Annotated[
            list[str] | None,
            Option(help='List of IPs or IP ranges to match (e.g. "123.123.123.123")')] = None,
        ports: Annotated[
            str | None,
            Option(help='Port or port range to match (e.g. "53", "1000-2000")')] = None,
        protocol: Annotated[
            list[str] | None,
            Option(help='List of protocols to match: http, tls, quic or bittorrent')] = None,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    xray_config = _init_and_load_config()

    if not (domain or ip or ports or protocol):
        print_error(Text(
            'At least one condition (domain, ip, ports, protocol) must be specified',
            STYLE_REGULAR))
        raise Exit(code=EXIT_ROUTING_NO_CONDITIONS)
    if protocol and not _is_correct_protocols(protocol):
        allowed_protocols = ', '.join(get_args(RuleProtocolType))
        print_error(Text.assemble(
            ('Invalid protocols: ', STYLE_REGULAR),
            (','.join(protocol), STYLE_ACCENT_NEUTRAL),
            ('. Allowed values: ', STYLE_REGULAR),
            (allowed_protocols, STYLE_VALUE)))
        raise Exit(code=EXIT_ROUTING_INVALID_PROTOCOLS)
    if ports and not _is_correct_ports_format(ports):
        print_error(Text.assemble(
            ('Invalid ports format: ', STYLE_REGULAR),
            (ports, STYLE_ACCENT_NEUTRAL)))
        raise Exit(code=EXIT_ROUTING_INVALID_PORTS)

    all_rules = _get_existing_rules(xray_config)
    rule_to_change = _find_rule_by_name(all_rules, name)

    if rule_to_change is None:
        print_error(Text.assemble(
            ('Rule ', STYLE_REGULAR),
            (name, STYLE_ACCENT_NEUTRAL),
            (' not found', STYLE_REGULAR)))
        raise Exit(code=EXIT_ROUTING_RULE_NOT_FOUND)

    if action == 'put':
        _add_conditions(rule_to_change, domain, ip, ports, protocol) # pyright: ignore[reportArgumentType]
    else:
        _remove_conditions(rule_to_change, domain, ip, ports, protocol) # pyright: ignore[reportArgumentType]

    _save_rules(xray_config, all_rules)
    stdout_console.print(Text.assemble(
        ('Rule ', STYLE_REGULAR),
        (name, STYLE_ACCENT_UP),
        (' changed', STYLE_REGULAR)))


@routing.command(help='Set domain strategy')
@error_handler(default_message='Error setting domain strategy', default_code=EXIT_ROUTING_ERROR)
def set_domain_strategy(
        strategy: Annotated[RoutingDomainStrategyType, Argument(help='domain strategy value')],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    xray_config = _init_and_load_config()

    if not xray_config.routing or not xray_config.routing.rules:
        print_error(Text(
            'At least one rule must be defined to set domain strategy', STYLE_REGULAR))
        raise Exit(code=EXIT_ROUTING_NO_RULES)

    current_strategy = _get_domain_strategy(xray_config)
    if current_strategy == strategy:
        print_error(Text.assemble(
            ('Domain strategy is already set to ', STYLE_REGULAR),
            (strategy, STYLE_ACCENT_NEUTRAL)))
        raise Exit(code=EXIT_ROUTING_STRATEGY_SAME)

    xray_config.routing.domain_strategy = strategy
    save_config(xray_config, XRAY_CONFIG_PATH)
    stdout_console.print(Text.assemble(
        ('Domain strategy successfully changed to ', STYLE_REGULAR),
        (strategy, STYLE_VALUE)))


@routing.command(help='Change rule outbound', name='change-outbound')
@error_handler(default_message='Error changing rule outbound', default_code=EXIT_ROUTING_ERROR)
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
        print_error(Text.assemble(
            ('Rule ', STYLE_REGULAR),
            (name, STYLE_ACCENT_NEUTRAL),
            (' not found', STYLE_REGULAR)))
        raise Exit(code=EXIT_ROUTING_RULE_NOT_FOUND)

    if not _is_outbound_exists(xray_config, outbound):
        print_error(Text.assemble(
            ('Outbound ', STYLE_REGULAR),
            (outbound, STYLE_ACCENT_NEUTRAL),
            (' not found', STYLE_REGULAR)))
        raise Exit(code=EXIT_ROUTING_OUTBOUND_NOT_FOUND)

    if rule_to_change.outbound_name == outbound:
        print_error(Text.assemble(
            ('Rule ', STYLE_REGULAR),
            (name, STYLE_ACCENT_NEUTRAL),
            (' already uses outbound ', STYLE_REGULAR),
            (outbound, STYLE_ACCENT_NEUTRAL)))
        raise Exit(code=EXIT_ROUTING_RULE_SAME_VALUE)

    rule_to_change.outbound_name = outbound

    _save_rules(xray_config, all_rules)
    stdout_console.print(Text.assemble(
        ('Rule ', STYLE_REGULAR),
        (name, STYLE_ACCENT_UP),
        (' outbound changed to ', STYLE_REGULAR),
        (outbound, STYLE_VALUE)))


def _is_outbound_exists(xray_config: Xray, outbound_name: str) -> bool:
    for outbound in xray_config.outbounds or []:
        if getattr(outbound, 'tag', None) == outbound_name:
            return True
    return False

def _is_correct_ports_format(ports: str | None) -> bool:
    if not ports:
        return True
    return fullmatch(r'\d{1,5}(?:-\d{1,5})?(?:,\d{1,5}(?:-\d{1,5})?)*', ports) is not None

def _is_correct_protocols(protocols: list[str] | None) -> bool:
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
    return [RuleData.from_model(rule, i)
            for i, rule in enumerate(xray_config.routing and xray_config.routing.rules or [])]


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
            with stdout_console.status(Text('Installing GeoIP data', STYLE_REGULAR)):
                install_geo_data(GEO_IP_URL, XRAY_GEO_IP_DATA_PATH)
            stdout_console.print(Text('GeoIP data installed', STYLE_OK))
        if all_geo_site_rules and not XRAY_GEO_SITE_DATA_PATH.exists():
            with stdout_console.status(Text('Installing Geosite data', STYLE_REGULAR)):
                install_geo_data(GEO_SITE_URL, XRAY_GEO_SITE_DATA_PATH)
            stdout_console.print(Text('Geosite data installed', STYLE_OK))
    else:
        xray_config.routing = None
        get_vless_inbound(xray_config).sniffing.enabled = False

    save_config(xray_config, XRAY_CONFIG_PATH)


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


def _add_unique_items(existing: list[Any], new_items: list[Any]) -> list[Any]:
    existing_set = set(existing)
    result = list(existing)
    for item in new_items:
        if item not in existing_set:
            result.append(item)
            existing_set.add(item)
    return result
