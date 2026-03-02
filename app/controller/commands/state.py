from typing import Annotated
from time import sleep

from typer import Option, echo, Exit

from app.app import app
from app.controller.common import (
    error_handler,
    load_config,
    exit_if_xray_config_not_found,
    check_and_install,
    ClientData
)
from app.defaults import XRAY_CONFIG_PATH
from app.model.vless_outbound import VlessOutbound
from app.utils import (
    detect_veepeenet_versions,
    is_xray_service_running,
    stop_xray_service,
    restart_xray_service,
    is_xray_service_enabled,
    disable_xray_service,
    start_xray_service,
    enable_xray_service
)
from app.view import ServerView


@app.command(help='Show service status')
@error_handler(default_message='Error retrieving service status', default_code=30)
def status(json: Annotated[bool, Option(help='Show JSON formatted info')] = False,
           _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    exit_if_xray_config_not_found()
    check_and_install()

    xray_config = load_config(XRAY_CONFIG_PATH)
    versions = detect_veepeenet_versions()

    client_names: list[str] = []
    for client in xray_config.inbounds[0].settings.clients:
        client_data = ClientData.from_model(client, xray_config.inbounds[0].listen)
        client_names.append(client_data.name)

    outbounds: list[str] = []
    for outbound in xray_config.outbounds:
        if isinstance(outbound, VlessOutbound):
            outbounds.append(
                f'{outbound.tag}({outbound.settings.address}:{outbound.settings.port})')
        else:
            outbounds.append(outbound.tag)

    server_view = ServerView(
        veepeenet_version=versions.veepeenet_version,
        veepeenet_build=versions.veepeenet_build,
        xray_version=versions.xray_version,
        server_status='Running' if is_xray_service_running() else 'Stopped',
        server_host=xray_config.inbounds[0].listen,
        server_port=xray_config.inbounds[0].port,
        reality_address=xray_config.inbounds[0].stream_settings.reality_settings.dest,
        reality_names=xray_config.inbounds[0].stream_settings.reality_settings.server_names,
        clients=client_names,
        outbounds=outbounds)
    if json:
        echo(server_view.model_dump_json(exclude_none=True, indent=2))
    else:
        echo(repr(server_view))


@app.command(help='Start service')
@error_handler(default_message='Error starting service', default_code=30)
def start(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    exit_if_xray_config_not_found()
    check_and_install()

    if is_xray_service_running():
        echo('Service is already running')
        return
    start_xray_service()
    sleep(2)
    if not is_xray_service_enabled():
        enable_xray_service()
    if is_xray_service_running():
        echo('Service started')
    else:
        echo('Failed to start service', err=True)
        raise Exit(code=31)


@app.command(help='Stop service')
@error_handler(default_message='Error stopping service', default_code=30)
def stop(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    exit_if_xray_config_not_found()
    check_and_install()

    if not is_xray_service_running():
        echo('Service is not running')
        return
    stop_xray_service()
    sleep(2)
    if is_xray_service_running():
        echo('Failed to stop service', err=True)
        raise Exit(code=32)
    if is_xray_service_enabled():
        disable_xray_service()
    echo('Service stopped')


@app.command(help='Restart service')
@error_handler(default_message='Error restarting service',default_code=30)
def restart(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    exit_if_xray_config_not_found()
    check_and_install()

    restart_xray_service()
    sleep(2)
    if is_xray_service_running():
        if not is_xray_service_enabled():
            enable_xray_service()
        echo('Service restarted')
    else:
        echo('Failed to restart service', err=True)
        raise Exit(code=33)
