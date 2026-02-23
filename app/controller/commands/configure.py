from sys import exit as sys_exit
from typing import Annotated

from typer import Option

from app.app import app
from app.controller.common import load_config, check_and_install, error_handler
from app.defaults import (
    VLESS_LISTEN_PORT,
    REALITY_HOST,
    REALITY_PORT,
    XRAY_CONFIG_PATH,
    GEO_IP_URL,
    GEO_SITE_URL,
    XRAY_GEO_IP_DATA_PATH,
    XRAY_GEO_SITE_DATA_PATH,
)
from app.model.vless_inbound import (
    VlessInbound,
    StreamSettings as InboundStreamSettings,
    RealitySettings as InboundRealitySettings
)
from app.model.xray import Xray
from app.utils import (
    detect_current_ipv4,
    write_text_file,
    gen_xray_private_key,
    install_geo_data,
)


@app.command(help='Configure VLESS Reality Xray service')
@error_handler(default_message='Error during configuration service')
def config(
        host: Annotated[str, Option(
            help=('Public interface of server.'
                  ' Using `hostname -i` if not specified.'
                  ' It is recommended to specify manually.'))] = None,
        port: Annotated[int, Option(help='Inbound port.')] = VLESS_LISTEN_PORT,
        reality_host: Annotated[str, Option(help='Reality host.')] = REALITY_HOST,
        reality_port: Annotated[int, Option(help='Reality port.')] = REALITY_PORT,
        reality_names: Annotated[
            list[str],
            Option(help='Available Reality server names.',
                   show_default='Reality host')] = None,
        clean: Annotated[bool, Option(help='Override current configuration')] = False,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_and_install()
    if not host:
        host = detect_current_ipv4()
        if not host:
            raise RuntimeError('Cannot auto detect public host address.'
                               ' Please specify it manually via --host option')
        detect_host_address_answer = __confirm_host_detection(host)
        if not detect_host_address_answer:
            print('Please specify public host address manually via --host option')
            sys_exit(-1)

    if not XRAY_CONFIG_PATH.exists() or clean:
        if clean:
            answer = __confirm_config_rewriting()
            if not answer:
                print('Aborted')
                sys_exit(0)
        xray_config = __create_config(
            host, port, reality_host, reality_port, reality_names or [reality_host])
    else:
        xray_config = load_config(XRAY_CONFIG_PATH)
        xray_config = __update_config(xray_config, host, port, reality_host, reality_port)

    write_text_file(
        XRAY_CONFIG_PATH,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    print('Server configuration is done')


@app.command(help='Update geodata (geoip.dat and geosite.dat) for Xray')
@error_handler(default_message='Error during geodata updating')
def update_geodata() -> None:
    check_and_install()

    install_geo_data(GEO_IP_URL, XRAY_GEO_IP_DATA_PATH)
    install_geo_data(GEO_SITE_URL, XRAY_GEO_SITE_DATA_PATH)
    print('Geodata updated')


def __confirm_host_detection(host: str) -> bool:
    answer = input(f'Auto detected public host address is {host}, is it correct? (y/N): ')
    return answer.lower() == 'y'


def __confirm_config_rewriting() -> bool:
    answer = input('ATTENTION!!!'
                   'Xray config file already exists, are you sure to overwrite it? (y/N): ')
    return answer.lower() == 'y'


def __create_config(listen: str, listen_port: int,
                    reality_host: str, reality_port: int, reality_names: list[str]) -> Xray:
    vless_inbound = VlessInbound(
        listen=listen,
        port=listen_port,
        stream_settings=InboundStreamSettings(
            reality_settings=InboundRealitySettings(
                dest=f'{reality_host}:{reality_port}',
                server_names=reality_names,
                private_key=gen_xray_private_key(),
                short_ids=[])))
    return Xray(inbounds=[vless_inbound])


def __update_config(
        xray_config: Xray,
        listen: str,
        listen_port: int,
        reality_host: str,
        reality_port: int
) -> Xray:
    xray_config.inbounds[0].listen = listen
    xray_config.inbounds[0].port = listen_port
    xray_config.inbounds[0].stream_settings.reality_settings.dest = f'{reality_host}:{reality_port}'
    xray_config.inbounds[0].stream_settings.reality_settings.server_names[0] = reality_host
    return xray_config
