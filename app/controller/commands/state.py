from typing import Annotated

from typer import Option

from app.app import app
from app.controller.common import (
    error_handler,
    load_config,
    exit_if_xray_config_not_found,
    check_and_install,
    ClientData
)
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


@app.command(help='Show service status')
@error_handler(default_message='Error retrieving service status')
def status(json: Annotated[bool, Option(help='Show JSON formatted info')] = False,
           _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    exit_if_xray_config_not_found()
    check_and_install()

    xray_config = load_config(XRAY_CONFIG_PATH)
    versions = detect_veepeenet_versions()

    client_views: list[ClientView] = []
    for client in xray_config.inbounds[0].settings.clients:
        client_data = ClientData.from_model(client, xray_config.inbounds[0].listen)
        client_url = get_vless_client_url(client_data.name, xray_config)
        client_views.append(ClientView(
            name=client_data.name,
            url=client_url))

    server_view = ServerView(
        veepeenet_version=versions.veepeenet_version,
        veepeenet_build=versions.veepeenet_build,
        xray_version=versions.xray_version,
        server_status='Running' if is_xray_service_running() else 'Stopped',
        server_host=xray_config.inbounds[0].listen,
        server_port=xray_config.inbounds[0].port,
        reality_address=xray_config.inbounds[0].stream_settings.reality_settings.dest,
        reality_names=xray_config.inbounds[0].stream_settings.reality_settings.server_names,
        clients=client_views)
    if json:
        print(server_view.model_dump_json(exclude_none=True, indent=2))
    else:
        print(repr(server_view))


@app.command(help='Start service')
@error_handler(default_message='Error starting service')
def start(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    exit_if_xray_config_not_found()
    check_and_install()

    if is_xray_service_running():
        print('Service is already running')
        return
    start_xray_service()
    if not is_xray_service_enabled():
        enable_xray_service()
    print('Service started')


@app.command(help='Stop service')
@error_handler(default_message='Error stopping service')
def stop(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    exit_if_xray_config_not_found()
    check_and_install()

    if not is_xray_service_running():
        print('Service is not running')
        return
    stop_xray_service()
    if is_xray_service_enabled():
        disable_xray_service()
    print('Service stopped')


@app.command(help='Restart service')
@error_handler(default_message='Error restarting service')
def restart(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    exit_if_xray_config_not_found()
    check_and_install()

    if is_xray_service_running():
        stop_xray_service()
    start_xray_service()
    print('Service restarted')
