from typing import Annotated, get_args, cast, Any
from urllib.parse import urlparse, parse_qs, unquote

from rich.text import Text
from typer import Argument, Option, Exit

from app.cli import outbounds
from app.controller.common import (
    error_handler,
    load_config,
    check_xray_config,
    check_root,
    print_error,
    save_config,
    stdout_console,
)
from app.controller.completions import complete_outbound_name, complete_vless_outbound_name
from app.defaults import (
    XRAY_CONFIG_PATH,
    VLESS_OUTBOUND_SPIDER_X,
    VLESS_OUTBOUND_FINGERPRINT,
    VLESS_OUTBOUND_PORT,
    VLESS_SEND_INTERFACE,
    STYLE_REGULAR,
    STYLE_ACCENT_UP,
    STYLE_ACCENT_DOWN,
    STYLE_ACCENT_NEUTRAL,
    STYLE_VALUE,
    EXIT_OUTBOUND_ERROR,
    EXIT_OUTBOUND_EXISTS,
    EXIT_OUTBOUND_INVALID_SHORT_ID,
    EXIT_OUTBOUND_INVALID_URL,
    EXIT_OUTBOUND_INVALID_FINGERPRINT,
    EXIT_OUTBOUND_NOT_FOUND,
    EXIT_OUTBOUND_NO_CHANGES,
    EXIT_OUTBOUND_IN_USE,
)
from app.controller.commands.routing import get_routing_view
from app.model.types import FingerprintType
from app.model.vless_outbound import (
    Settings as OutboundSettings,
    RealitySettings as OutboundRealitySettings,
    VlessOutbound,
    StreamSettings as OutboundStreamSettings
)
from app.model.xray import Outbound, Xray
from app.utils import set_value, is_valid_vless_client_url
from app.view import OutboundsView, OutboundView


@outbounds.command(help='Show Vless outbounds', name='list')
@error_handler(default_message='Error retrieving Vless outbounds', default_code=EXIT_OUTBOUND_ERROR)
def show(
        json: Annotated[bool, Option(help='Show JSON formatted info')] = False,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_xray_config()
    xray_config = load_config(XRAY_CONFIG_PATH)

    view = get_outbounds_view(xray_config)

    if json:
        stdout_console.print_json(view.model_dump_json(exclude_none=True, indent=2))
    else:
        stdout_console.print(view.rich_repr())


def get_outbounds_view(xray_config: Xray) -> OutboundsView:
    outbound_views: list[OutboundView] = []
    for i, outbound in enumerate(xray_config.outbounds or []):
        default_name = f'outbound_{i}'
        if isinstance(outbound, VlessOutbound):
            outbound_views.append(OutboundView(
                name=outbound.tag or default_name,
                address=outbound.settings.address,
                port=outbound.settings.port,
                uuid=outbound.settings.id,
                sni=outbound.stream_settings.reality_settings.server_name,
                short_id=outbound.stream_settings.reality_settings.short_id,
                password=outbound.stream_settings.reality_settings.password,
                spider_x=outbound.stream_settings.reality_settings.spider_x,
                fingerprint=outbound.stream_settings.reality_settings.fingerprint,
                interface=outbound.send_through,
            ))
        else:
            outbound_views.append(OutboundView(name=getattr(outbound, 'tag', None) or default_name))
    return OutboundsView(outbounds=outbound_views)


@outbounds.command(help='Add new Vless outbound to service')
@error_handler(default_message='Error adding Vless outbound connection',
               default_code=EXIT_OUTBOUND_ERROR)
def add(
        name: Annotated[str, Argument(help='Outbound name')],
        address: Annotated[str, Option(help='Outbound address (ip or domain name)')],
        uuid: Annotated[str, Option(help='Vless client identifier')],
        sni: Annotated[str, Option(help='Server name of target server')],
        short_id: Annotated[str, Option(help='One of short_id of target server')],
        password: Annotated[str, Option(help='Public key of target server')],
        spider_x: Annotated[
            str,
            Option(help='Initial path and parameters for the spider')] = VLESS_OUTBOUND_SPIDER_X,
        port: Annotated[
            int | None,
            Option(help='Vless outbound port')] = VLESS_OUTBOUND_PORT,
        fingerprint: Annotated[
            FingerprintType,
            Option(help='Browser TLS Client Hello fingerprint')] = VLESS_OUTBOUND_FINGERPRINT,
        interface: Annotated[
            str, Option(help='Send through interface')] = VLESS_SEND_INTERFACE,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()

    xray_config = load_config(XRAY_CONFIG_PATH)
    for outbound in xray_config.outbounds or []:
        tag_value = getattr(outbound, 'tag', None)
        if tag_value == name:
            print_error(Text.assemble(
                ('Outbound ', STYLE_REGULAR),
                (name, STYLE_ACCENT_NEUTRAL),
                (' already exists', STYLE_REGULAR)))
            raise Exit(code=EXIT_OUTBOUND_EXISTS)

    if len(short_id) % 2 != 0:
        print_error(Text('Invalid sid (short_id): length must be even', STYLE_REGULAR))
        raise Exit(code=EXIT_OUTBOUND_INVALID_SHORT_ID)

    reality_settings = OutboundRealitySettings(
        server_name=sni,
        fingerprint=fingerprint,
        password=password,
        short_id=short_id,
        spider_x=spider_x
    )
    new_outbound = VlessOutbound(
        tag=name,
        send_through=interface,
        settings=OutboundSettings(address=address, id=uuid, port=port or VLESS_OUTBOUND_PORT),
        stream_settings=OutboundStreamSettings(
            reality_settings=reality_settings,
        )
    )

    if xray_config.outbounds is None:
        xray_config.outbounds = [new_outbound]
    else:
        xray_config.outbounds.append(new_outbound)
    save_config(xray_config, XRAY_CONFIG_PATH)
    stdout_console.print(Text.assemble(
        ('Added new outbound ', STYLE_REGULAR),
        (name, STYLE_ACCENT_UP)))


@outbounds.command(help='Add new Vless outbound to service from URL')
@error_handler(default_message='Error adding Vless outbound connection from URL',
               default_code=EXIT_OUTBOUND_ERROR)
def add_from_url(
        url: Annotated[str, Argument(help='Outbound URL')],
        name: Annotated[str | None, Option(help='Outbound name')] = None,
        interface: Annotated[
            str, Option(help='Send through interface')] = VLESS_SEND_INTERFACE,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    if not is_valid_vless_client_url(url):
        print_error(Text('Unsupported Vless client URL', STYLE_REGULAR))
        raise Exit(code=EXIT_OUTBOUND_INVALID_URL)

    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    address = parsed_url.hostname
    port = parsed_url.port
    uuid = parsed_url.username
    sni = query_params.get('sni', [''])[0]
    password = query_params.get('pbk', [''])[0]
    short_id = query_params.get('sid', [''])[0]
    spider_x = unquote(query_params.get('spx', [''])[0])
    fingerprint = query_params.get('fp', [''])[0]
    outbound_name = name or parsed_url.fragment

    if fingerprint not in get_args(FingerprintType):
        print_error(Text.assemble(
            ('Unsupported fingerprint: ', STYLE_REGULAR),
            (fingerprint, STYLE_ACCENT_NEUTRAL)))
        raise Exit(code=EXIT_OUTBOUND_INVALID_FINGERPRINT)
    fingerprint = cast(FingerprintType, fingerprint)

    add(name=outbound_name, address=address, uuid=uuid, sni=sni, password=password,
        short_id=short_id, spider_x=spider_x, port=port,
        fingerprint=fingerprint, interface=interface, _debug=_debug)



@outbounds.command(help='Remove Vless outbound from service')
@error_handler(default_message='Error removing Vless outbound connection',
               default_code=EXIT_OUTBOUND_ERROR)
def remove(
        name: Annotated[str, Argument(
            help='Outbound name', autocompletion=complete_vless_outbound_name)],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()

    xray_config = load_config(XRAY_CONFIG_PATH)
    outs = xray_config.outbounds or []
    for outbound in outs:
        if isinstance(outbound, VlessOutbound) and outbound.tag == name:
            routing_view = get_routing_view(xray_config)
            used_in_rules = [rule.name for rule in (routing_view.rules or [])
                             if rule.outbound_name == name]
            if used_in_rules:
                print_error(Text.assemble(
                    ('Vless outbound ', STYLE_REGULAR),
                    (name, STYLE_ACCENT_NEUTRAL),
                    (' is used in rules: ', STYLE_REGULAR),
                    (', '.join(used_in_rules), STYLE_VALUE),
                    ('. Remove the rules first.', STYLE_REGULAR)))
                raise Exit(code=EXIT_OUTBOUND_IN_USE)
            outs.remove(outbound)
            save_config(xray_config, XRAY_CONFIG_PATH)
            stdout_console.print(Text.assemble(
                ('Removed Vless outbound ', STYLE_REGULAR),
                (name, STYLE_ACCENT_DOWN)))
            return
    print_error(Text.assemble(
        ('Vless outbound ', STYLE_REGULAR),
        (name, STYLE_ACCENT_NEUTRAL),
        (' not found', STYLE_REGULAR)))
    raise Exit(code=EXIT_OUTBOUND_NOT_FOUND)


@outbounds.command(help='Set outbound as default (move to first position)')
@error_handler(default_message='Error setting default outbound', default_code=EXIT_OUTBOUND_ERROR)
def set_default(
        name: Annotated[str, Argument(help='Outbound name', autocompletion=complete_outbound_name)],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()

    xray_config = load_config(XRAY_CONFIG_PATH)
    target_outbound: Outbound | dict[str, Any] | None = None
    outs = xray_config.outbounds or []
    for outbound in outs:
        tag_value = getattr(outbound, 'tag', None)
        if tag_value == name:
            target_outbound = outbound
            break
    if not target_outbound:
        print_error(Text.assemble(
            ('Outbound ', STYLE_REGULAR),
            (name, STYLE_ACCENT_NEUTRAL),
            (' not found', STYLE_REGULAR)))
        raise Exit(code=EXIT_OUTBOUND_NOT_FOUND)

    outs.remove(target_outbound)
    outs.insert(0, target_outbound)
    save_config(xray_config, XRAY_CONFIG_PATH)
    stdout_console.print(Text.assemble(
        ('Outbound ', STYLE_REGULAR),
        (name, STYLE_ACCENT_UP),
        (' is now the default', STYLE_REGULAR)))


@outbounds.command(help='Change Vless outbound')
@error_handler(default_message='Error changing Vless outbound connection',
               default_code=EXIT_OUTBOUND_ERROR)
def change(
        name: Annotated[str, Argument(
            help='Vless outbound name', autocompletion=complete_vless_outbound_name)],
        address: Annotated[str | None, Option(help='Outbound address (ip or domain name)')] = None,
        uuid: Annotated[str | None, Option(help='Vless client identifier')] = None,
        sni: Annotated[str | None, Option(help='Server name of target server')] = None,
        password: Annotated[str | None, Option(help='Public key of target server')] = None,
        short_id: Annotated[str | None, Option(help='One of short_id of target server')] = None,
        spider_x: Annotated[
            str | None,
            Option(help='Initial path and parameters for the spider')] = None,
        port: Annotated[
            int | None,
            Option(help='Vless outbound port')] = None,
        fingerprint: Annotated[
            FingerprintType | None,
            Option(help='Browser TLS Client Hello fingerprint')] = VLESS_OUTBOUND_FINGERPRINT,
        interface: Annotated[
            str | None, Option(help='Send through interface')] = None,
        new_name: Annotated[str | None, Option(help='New outbound name')] = None,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()

    xray_config = load_config(XRAY_CONFIG_PATH)
    target_outbound: VlessOutbound | None = None
    for outbound in xray_config.outbounds or []:
        if isinstance(outbound, VlessOutbound) and outbound.tag == name:
            target_outbound = outbound
    if not target_outbound:
        print_error(Text.assemble(
            ('Vless outbound ', STYLE_REGULAR),
            (name, STYLE_ACCENT_NEUTRAL),
            (' not found', STYLE_REGULAR)))
        raise Exit(code=EXIT_OUTBOUND_NOT_FOUND)

    if short_id and len(short_id) % 2 != 0:
        print_error(Text('Invalid sid (short_id): length must be even', STYLE_REGULAR))
        raise Exit(code=EXIT_OUTBOUND_INVALID_SHORT_ID)

    results = [set_value(target_outbound, 'tag', new_name),
               set_value(target_outbound, 'send_through', interface),
               set_value(target_outbound.settings, 'address', address),
               set_value(target_outbound.settings, 'port', port),
               set_value(target_outbound.settings, 'id', uuid),
               set_value(target_outbound.stream_settings.reality_settings, 'server_name', sni),
               set_value(target_outbound.stream_settings.reality_settings, 'password', password),
               set_value(target_outbound.stream_settings.reality_settings, 'short_id', short_id),
               set_value(target_outbound.stream_settings.reality_settings, 'spider_x', spider_x),
               set_value(target_outbound.stream_settings.reality_settings, 'fingerprint', fingerprint)]
    if not any(results):
        print_error(Text.assemble(
            ('No changes found for outbound ', STYLE_REGULAR),
            (name, STYLE_ACCENT_NEUTRAL)))
        raise Exit(code=EXIT_OUTBOUND_NO_CHANGES)

    save_config(xray_config, XRAY_CONFIG_PATH)
    stdout_console.print(Text.assemble(
        ('Changed outbound ', STYLE_REGULAR),
        (name, STYLE_ACCENT_UP)))
