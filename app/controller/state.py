from pathlib import Path

from app.controller.common import load_config, ClientData
from app.defaults import XRAY_CONFIG_PATH
from app.utils import (
    detect_veepeenet_versions,
    get_vless_client_url,
    is_xray_service_running, stop_xray_service,
    is_xray_service_enabled,
    disable_xray_service,
    start_xray_service,
    enable_xray_service
)
from app.view import ServerView, ClientView


def status(xray_config_path: Path = XRAY_CONFIG_PATH) -> ServerView:
    xray_config = load_config(xray_config_path)
    versions = detect_veepeenet_versions()

    client_views: list[ClientView] = []
    for client in xray_config.inbounds[0].settings.clients:
        client_data = ClientData.from_model(client, xray_config.inbounds[0].listen)
        client_url = get_vless_client_url(client_data.name, xray_config)
        client_views.append(ClientView(
            name=client_data.name,
            url=client_url))

    return ServerView(
        veepeenet_version=versions.veepeenet_version,
        veepeenet_build=versions.veepeenet_build,
        xray_version=versions.xray_version,
        server_status='Running' if is_xray_service_running() else 'Stopped',
        server_host=xray_config.inbounds[0].listen,
        server_port=xray_config.inbounds[0].port,
        reality_address=xray_config.inbounds[0].stream_settings.reality_settings.dest,
        reality_names=xray_config.inbounds[0].stream_settings.reality_settings.server_names,
        clients=client_views)


def stop() -> None:
    if not is_xray_service_running():
        print('Xray service is not running')
        return
    stop_xray_service()
    if is_xray_service_enabled():
        disable_xray_service()
    print('Xray service stopped')


def start() -> None:
    if is_xray_service_running():
        print('Xray service is already running')
        return
    start_xray_service()
    if not is_xray_service_enabled():
        enable_xray_service()
    print('Xray service started')


def restart() -> None:
    if is_xray_service_running():
        stop_xray_service()
    start_xray_service()
    print('Xray service restarted')
