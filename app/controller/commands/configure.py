from typing import Annotated
from uuid import uuid4

from typer import Option, echo, Exit

from app.cli import app
from app.controller.common import (
    load_config,
    check_root,
    check_distrib,
    error_handler,
    get_vless_inbound,
)
from app.defaults import (
    VLESS_LISTEN_INTERFACE,
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
from app.model.veepeenet import VeePeeNET
from app.utils import (
    detect_current_ipv4,
    write_text_file,
    gen_xray_private_key,
    install_geo_data,
)


@app.command(help='Configure VLESS Reality Xray service')
@error_handler(default_message='Error during configuration service', default_code=10)
def config(
        host: Annotated[str | None, Option(
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
    check_root()
    check_distrib()
    if not host:
        host = detect_current_ipv4()
        if not host:
            echo('Cannot auto detect public host address.'
                 ' Please specify it manually via --host option',
                 err=True)
            raise Exit(code=11)
        detect_host_address_answer = _confirm_host_detection(host)
        if not detect_host_address_answer:
            echo('Please specify public host address manually via --host option', err=True)
            raise Exit(code=12)

    if not XRAY_CONFIG_PATH.exists() or clean:
        if clean:
            answer = _confirm_config_rewriting()
            if not answer:
                echo('Aborted')
                return
        xray_config = _create_config(
            host, port, reality_host, reality_port, reality_names or [reality_host])
    else:
        xray_config = load_config(XRAY_CONFIG_PATH)
        xray_config = _update_config(
            xray_config, host, port, reality_host, reality_port, reality_names or [reality_host])

    write_text_file(
        XRAY_CONFIG_PATH,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    echo('Server configuration is done')


@app.command(help='Update geodata (geoip.dat and geosite.dat) for Xray')
@error_handler(default_message='Error during geodata updating', default_code=10)
def update_geodata() -> None:
    check_root()

    install_geo_data(GEO_IP_URL, XRAY_GEO_IP_DATA_PATH)
    install_geo_data(GEO_SITE_URL, XRAY_GEO_SITE_DATA_PATH)
    echo('Geodata updated')


def _confirm_host_detection(host: str) -> bool:
    answer = input(f'Auto detected public host address is {host}, is it correct? (y/N): ')
    return answer.lower() == 'y'


def _confirm_config_rewriting() -> bool:
    answer = input('ATTENTION!!! '
                   'Xray config file already exists, are you sure to overwrite it? (y/N): ')
    return answer.lower() == 'y'


def _create_config(host: str, listen_port: int,
                    reality_host: str, reality_port: int, reality_names: list[str]) -> Xray:
    vless_inbound = VlessInbound(
        listen=VLESS_LISTEN_INTERFACE,
        port=listen_port,
        stream_settings=InboundStreamSettings(
            reality_settings=InboundRealitySettings(
                dest=f'{reality_host}:{reality_port}',
                server_names=reality_names,
                private_key=gen_xray_private_key(),
                short_ids=[])))
    veepeenet = VeePeeNET(host=host, namespace=str(uuid4()))
    return Xray(veepeenet=veepeenet, inbounds=[vless_inbound])


def _update_config(
        xray_config: Xray,
        host: str,
        listen_port: int,
        reality_host: str,
        reality_port: int,
        reality_names: list[str]
) -> Xray:
    xray_config.veepeenet.host = host
    vless_inbound = get_vless_inbound(xray_config)
    vless_inbound.port = listen_port
    vless_inbound.stream_settings.reality_settings.dest = f'{reality_host}:{reality_port}'
    vless_inbound.stream_settings.reality_settings.server_names = reality_names
    return xray_config
