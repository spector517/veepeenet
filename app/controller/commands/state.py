from typing import Annotated

from rich.text import Text
from typer import Option, Exit

from app.cli import app
from app.controller.common import (
    error_handler,
    load_config,
    check_xray_config,
    check_root,
    check_distrib,
    get_vless_inbound,
    start_service,
    stop_service,
    restart_service,
    print_error,
    ClientData, stdout_console,
)
from app.defaults import (
    XRAY_CONFIG_PATH,
    XRAY_CONFIG_BACKUP_PATH,
    STYLE_REGULAR,
    EXIT_STATE_ERROR,
    EXIT_STATE_START_FAILED,
    EXIT_STATE_STOP_FAILED,
    EXIT_STATE_RESTART_FAILED,
)
from app.model.vless_outbound import VlessOutbound
from app.utils import (
    detect_veepeenet_versions,
    get_xray_distrib_version,
    is_xray_service_running,
    is_xray_service_enabled,
    get_xray_service_uptime,
    is_files_content_same,
)
from app.view import ServerView, OutboundView


@app.command(help='Show service status')
@error_handler(default_message='Error retrieving service status', default_code=EXIT_STATE_ERROR)
def status(json: Annotated[bool, Option(help='Show JSON formatted info')] = False,
           _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_xray_config()
    check_distrib()

    xray_config = load_config(XRAY_CONFIG_PATH)
    inbound = get_vless_inbound(xray_config)
    versions = detect_veepeenet_versions()
    xray_version = get_xray_distrib_version()
    running = is_xray_service_running()

    client_names: list[str] = []
    for i, client in enumerate(inbound.settings.clients or []):
        client_data = ClientData.from_model(client, i)
        client_names.append(client_data.name)

    outbounds: list[OutboundView] = []
    for i, outbound in enumerate(xray_config.outbounds or []):
        default_name = f'outbound_{i}'
        if isinstance(outbound, VlessOutbound):
            outbounds.append(OutboundView(
                name=outbound.tag or default_name,
                address=f'{outbound.settings.address}:{outbound.settings.port}'))
        else:
            outbounds.append(OutboundView(name=getattr(outbound, 'tag', None) or default_name))

    if not xray_config.veepeenet:
        print_error(Text('Invalid configuration: missing veepeenet section', STYLE_REGULAR))
        raise Exit(code=EXIT_STATE_ERROR)

    server_view = ServerView(
        veepeenet_version=versions.veepeenet_version,
        veepeenet_build=versions.veepeenet_build,
        xray_version=xray_version or 'None',
        server_status='running' if running else 'stopped',
        enabled=is_xray_service_enabled(),
        uptime=get_xray_service_uptime() if running else None,
        restart_required=not is_files_content_same(XRAY_CONFIG_PATH, XRAY_CONFIG_BACKUP_PATH),
        server_host=xray_config.veepeenet.host,
        server_port=str(inbound.port),
        reality_address=inbound.stream_settings.reality_settings.dest,
        reality_names=inbound.stream_settings.reality_settings.server_names,
        clients=client_names,
        outbounds=outbounds,
        server_name=xray_config.veepeenet.name)
    if json:
        stdout_console.print_json(
            server_view.model_dump_json(exclude_none=True),
            indent=2)
    else:
        stdout_console.print(server_view.rich_repr())


@app.command(help='Start service')
@error_handler(default_message='Error starting service', default_code=EXIT_STATE_ERROR)
def start(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()
    check_distrib()

    try:
        start_service()
    except RuntimeError as e:
        print_error(Text('Failed to start service', STYLE_REGULAR))
        raise Exit(code=EXIT_STATE_START_FAILED) from e


@app.command(help='Stop service')
@error_handler(default_message='Error stopping service', default_code=EXIT_STATE_ERROR)
def stop(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()
    check_distrib()

    try:
        stop_service()
    except RuntimeError as e:
        print_error(Text('Failed to stop service', STYLE_REGULAR))
        raise Exit(code=EXIT_STATE_STOP_FAILED) from e


@app.command(help='Restart service')
@error_handler(default_message='Error restarting service', default_code=EXIT_STATE_ERROR)
def restart(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_xray_config()
    check_distrib()

    try:
        restart_service()
    except RuntimeError as e:
        print_error(Text('Failed to restart service', STYLE_REGULAR))
        raise Exit(code=EXIT_STATE_RESTART_FAILED) from e
