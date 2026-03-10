from typing import Annotated, get_args, cast
from urllib.parse import urlparse, parse_qs, unquote

from rich.text import Text
from typer import Argument, Option, Exit

from app.cli import outbounds
from app.controller.common import (
    error_handler,
    load_config,
    check_xray_config,
    check_root,
    stdout_console,
    print_error,
)
from app.defaults import (
    XRAY_CONFIG_PATH,
    VLESS_OUTBOUND_SPIDER_X,
    VLESS_OUTBOUND_FINGERPRINT,
    VLESS_OUTBOUND_PORT,
)
from app.model.types import FingerprintType
from app.model.vless_outbound import (
    Settings as OutboundSettings,
    RealitySettings as OutboundRealitySettings,
    VlessOutbound,
    StreamSettings as OutboundStreamSettings
)
from app.model.xray import Outbound
from app.utils import write_text_file, set_value, is_valid_vless_client_url


@outbounds.command(help='Add new VLESS outbound to service')
@error_handler(default_message='Error adding VLESS outbound connection', default_code=40)
def add(
        name: Annotated[str, Argument(help='Outbound name')],
        address: Annotated[str, Option(help='Outbound address (ip or domain name)')],
        uuid: Annotated[str, Option(help='VLESS client identifier')],
        sni: Annotated[str, Option(help='Server name of target server')],
        short_id: Annotated[str, Option(help='One of short_id of target server')],
        password: Annotated[str, Option(help='Public key of target server')] = '',
        spider_x: Annotated[
            str,
            Option(help='Initial path and parameters for the spider')] = VLESS_OUTBOUND_SPIDER_X,
        port: Annotated[
            int | None,
            Option(help='VLESS outbound port')] = VLESS_OUTBOUND_PORT,
        fingerprint: Annotated[
            FingerprintType,
            Option(help='Fingerprint of target server')] = VLESS_OUTBOUND_FINGERPRINT,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()

    xray_config = load_config(XRAY_CONFIG_PATH)
    for outbound in xray_config.outbounds:
        if outbound.tag == name:
            print_error(Text.assemble(
                'VLESS outbound ', (f'{name}', 'bold yellow'), ' already exists'))
            raise Exit(code=41)

    if len(short_id) % 2 != 0:
        print_error('Invalid sid (short_id): length must be even')
        raise Exit(code=42)

    settings = OutboundSettings(address=address, id=uuid, port=port)
    reality_settings = OutboundRealitySettings(
        server_name=sni,
        fingerprint=fingerprint,
        password=password,
        short_id=short_id,
        spider_x=spider_x
    )
    new_outbound = VlessOutbound(
        tag=name,
        settings=settings,
        stream_settings=OutboundStreamSettings(
            reality_settings=reality_settings,
        )
    )

    xray_config.outbounds.append(new_outbound)
    write_text_file(
        XRAY_CONFIG_PATH,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    print_error(Text.assemble('Added new outbound ', (f'{name}', 'bold green')))


@outbounds.command(help='Add new VLESS outbound to service from URL')
@error_handler(default_message='Error adding VLESS outbound connection from URL', default_code=40)
def add_from_url(
        url: Annotated[str, Argument(help='Outbound URL')],
        name: Annotated[str | None, Option(help='Outbound name')] = None,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    if not is_valid_vless_client_url(url):
        print_error('Unsupported VLESS client URL')
        raise Exit(code=43)

    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    address = parsed_url.hostname
    port = parsed_url.port
    uuid = parsed_url.username
    sni = query_params.get('sni')[0]
    password = query_params.get('pbk')[0]
    short_id = query_params.get('sid', [''])[0]
    spider_x = unquote(query_params.get('spx')[0])
    fingerprint = query_params.get('fp')[0]
    outbound_name = name or parsed_url.fragment

    if fingerprint not in get_args(FingerprintType):
        print_error(
            Text.assemble('Unsupported fingerprint: ', (fingerprint, 'bold yellow')))
        raise Exit(code=44)
    fingerprint = cast(FingerprintType, fingerprint)

    add(name=outbound_name, address=address, uuid=uuid, sni=sni, password=password,
        short_id=short_id, spider_x=spider_x, port=port,
        fingerprint=fingerprint, _debug=_debug)



@outbounds.command(help='Remove VLESS outbound from service')
@error_handler(default_message='Error removing VLESS outbound connection', default_code=40)
def remove(
        name: Annotated[str, Argument(help='Outbound name')],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()

    xray_config = load_config(XRAY_CONFIG_PATH)
    for outbound in xray_config.outbounds:
        if outbound.tag == name and outbound.protocol == 'vless':
            xray_config.outbounds.remove(outbound)
            write_text_file(
                XRAY_CONFIG_PATH,
                xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
                0o644)
            stdout_console.print(Text.assemble('Removed outbound ', (f'{name}', 'bold red')))
            return
    print_error(
        Text.assemble('VLESS outbound ', (f'{name}', 'bold yellow'), ' not found'))
    raise Exit(code=45)


@outbounds.command(help='Set outbound as default (move to first position)')
@error_handler(default_message='Error setting default outbound', default_code=40)
def set_default(
        name: Annotated[str, Argument(help='Outbound name')],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()

    xray_config = load_config(XRAY_CONFIG_PATH)
    target_outbound: Outbound | None = None
    for outbound in xray_config.outbounds:
        if outbound.tag == name:
            target_outbound = outbound
            break
    if not target_outbound:
        print_error(Text.assemble('Outbound ', (f'{name}', 'bold yellow'), ' not found'))
        raise Exit(code=45)

    xray_config.outbounds.remove(target_outbound)
    xray_config.outbounds.insert(0, target_outbound)
    write_text_file(
        XRAY_CONFIG_PATH,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    stdout_console.print(
        Text.assemble('Outbound ', (f'{name}', 'bold green'), ' is now the default'))


@outbounds.command(help='Change VLESS outbound')
@error_handler(default_message='Error changing VLESS outbound connection', default_code=40)
def change(
        name: Annotated[str, Argument(help='Outbound name')],
        address: Annotated[str | None, Option(help='Outbound address (ip or domain name)')] = None,
        uuid: Annotated[str | None, Option(help='VLESS client identifier')] = None,
        sni: Annotated[str | None, Option(help='Server name of target server')] = None,
        password: Annotated[str | None, Option(help='Public key of target server')] = None,
        short_id: Annotated[str | None, Option(help='One of short_id of target server')] = None,
        spider_x: Annotated[
            str | None,
            Option(help='Initial path and parameters for the spider')] = None,
        port: Annotated[
            int | None,
            Option(help='VLESS outbound port')] = None,
        new_name: Annotated[str | None, Option(help='New outbound name')] = None,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()

    xray_config = load_config(XRAY_CONFIG_PATH)
    target_outbound: VlessOutbound | None = None
    for outbound in xray_config.outbounds:
        if outbound.tag == name and outbound.protocol == 'vless':
            target_outbound = outbound
    if not target_outbound:
        print_error(
            Text.assemble('VLESS outbound ', (f'{name}', 'bold yellow'), ' not found'))
        raise Exit(code=45)

    if short_id and len(short_id) % 2 != 0:
        print_error(
            'Invalid sid (short_id): length must be even')
        raise Exit(code=42)

    results = [set_value(target_outbound, 'tag', new_name),
               set_value(target_outbound.settings, 'address', address),
               set_value(target_outbound.settings, 'port', port),
               set_value(target_outbound.settings, 'id', uuid),
               set_value(target_outbound.stream_settings.reality_settings, 'server_name', sni),
               set_value(target_outbound.stream_settings.reality_settings, 'password', password),
               set_value(target_outbound.stream_settings.reality_settings, 'short_id', short_id),
               set_value(target_outbound.stream_settings.reality_settings, 'spider_x', spider_x)]
    if not any(results):
        print_error(
            Text.assemble('No changes found for outbound ', (f'{name}', 'bold yellow')))
        raise Exit(code=46)

    write_text_file(
        XRAY_CONFIG_PATH,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    stdout_console.print(Text.assemble('Changed outbound ', (f'{name}', 'bold green')))
