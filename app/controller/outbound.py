from pathlib import Path
from sys import exit as sys_exit

from app.controller.common import load_config
from app.defaults import XRAY_CONFIG_PATH
from app.model.vless_outbound import (
    Settings as OutboundSettings,
    RealitySettings as OutboundRealitySettings,
    VlessOutbound,
    StreamSettings as OutboundStreamSettings
)
from app.utils import write_text_file, set_value


def add_vless_outbound(
        tag: str,
        address: str,
        port: int,
        uuid: str,
        server_name: str,
        password: str,
        short_id: str,
        spider_x: str,
        xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    xray_config = load_config(xray_config_path)
    for outbound in xray_config.outbounds:
        if outbound.tag == tag:
            print(f'Outbound with tag {tag} already exists')
            return

    settings = OutboundSettings(address=address, id=uuid, port=port)
    if port:
        settings.port = port
    reality_settings = OutboundRealitySettings(
        server_name=server_name,
        fingerprint='chrome',
        password=password,
        short_id=short_id,
        spider_x=spider_x
    )
    new_outbound = VlessOutbound(
        tag=tag,
        settings=settings,
        stream_settings=OutboundStreamSettings(
            reality_settings=reality_settings,
        )
    )

    xray_config.outbounds.append(new_outbound)
    write_text_file(
        xray_config_path,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    print('Added new VLESS outbound with tag', tag)


def remove_vless_outbound(tag: str, xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    xray_config = load_config(xray_config_path)
    for outbound in xray_config.outbounds:
        if outbound.tag == tag and outbound.protocol == 'vless':
            xray_config.outbounds.remove(outbound)
            write_text_file(
                xray_config_path,
                xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
                0o644)
            print('Removed VLESS outbound with tag:', tag)
            return
    print(f'VLESS outbound {tag} not found')
    sys_exit(-1)


def change_vless_outbound(
        tag: str,
        address: str | None,
        port: int | None,
        uuid: str | None,
        server_name: str | None,
        password: str | None,
        short_id: str | None,
        spider_x: str | None,
        xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    xray_config = load_config(xray_config_path)
    target_outbound: VlessOutbound | None = None
    for outbound in xray_config.outbounds:
        if outbound.tag == tag and outbound.protocol == 'vless':
            target_outbound = outbound
    if not target_outbound:
        print(f'VLESS outbound {tag} not found')
        sys_exit(-1)

    results = [set_value(target_outbound.settings, 'address', address),
        set_value(target_outbound.settings, 'address', address),
        set_value(target_outbound.settings, 'port', port),
        set_value(target_outbound.settings, 'id', uuid),
        set_value(target_outbound.stream_settings.reality_settings, 'server_name', server_name),
        set_value(target_outbound.stream_settings.reality_settings, 'password', password),
        set_value(target_outbound.stream_settings.reality_settings, 'short_id', short_id),
        set_value(target_outbound.stream_settings.reality_settings, 'spider_x', spider_x)]
    if not any(results):
        print('No changes found')
        sys_exit(-1)

    write_text_file(
        xray_config_path,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    print('Changed VLESS outbound with tag:', tag)
