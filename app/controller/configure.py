from pathlib import Path
from sys import exit as sys_exit

from app.controller.common import load_config
from app.defaults import XRAY_CONFIG_PATH
from app.model.vless_inbound import (
    VlessInbound,
    StreamSettings as InboundStreamSettings,
    RealitySettings as InboundRealitySettings
)
from app.model.xray import Xray
from app.utils import detect_current_ipv4, write_text_file, gen_xray_private_key


def config(
        listen: str,
        listen_port: int,
        reality_host: str,
        reality_port: int,
        clean: bool,
        xray_config_path: Path = XRAY_CONFIG_PATH
) -> None:
    if not listen:
        listen = detect_current_ipv4()
    if not listen:
        raise RuntimeError('Cannot auto detect public host address.'
                           ' Please specify it manually via --host option')
    detect_host_address_answer = confirm_host_detection(listen)
    if not detect_host_address_answer:
        raise RuntimeError('Please specify it manually via --host option')

    if not xray_config_path.exists() or clean:
        if clean:
            answer = confirm_config_rewriting()
            if not answer:
                print('Aborted')
                sys_exit(0)

        xray_config = create_config(listen, listen_port, reality_host, reality_port)
    else:
        xray_config = load_config(XRAY_CONFIG_PATH)
        xray_config = update_config(xray_config, listen, listen_port, reality_host, reality_port)

    write_text_file(
        xray_config_path,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    print('Configuration completed')


def confirm_host_detection(host: str) -> bool:
    answer = input(f'Auto detected public host address is {host}, is it correct? (y/N): ')
    return answer.lower() == 'y'


def confirm_config_rewriting() -> bool:
    answer = input('ATTENTION!!!'
                   'Xray config file already exists, are you sure to overwrite it? (y/N): ')
    return answer.lower() == 'y'


def create_config(listen: str, listen_port: int, reality_host: str, reality_port: int) -> Xray:
    vless_inbound = VlessInbound(
        listen=listen,
        port=listen_port,
        stream_settings=InboundStreamSettings(
            reality_settings=InboundRealitySettings(
                dest=f'{reality_host}:{reality_port}',
                server_names=[reality_host],
                private_key=gen_xray_private_key(),
                short_ids=[])))
    return Xray(inbounds=[vless_inbound])


def update_config(
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
