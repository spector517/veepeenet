from typing import Annotated
from urllib.parse import urljoin
from uuid import uuid4

from rich.prompt import Prompt, Confirm
from rich.text import Text
from typer import Option, Exit

from app.cli import app
from app.controller.common import (
    load_config,
    check_root,
    check_distrib,
    error_handler,
    get_vless_inbound,
    start_service,
    stop_service,
    stdout_console,
    print_error,
    save_config,
)
from app.defaults import (
    VLESS_LISTEN_INTERFACE,
    VLESS_LISTEN_PORT,
    REALITY_HOST,
    REALITY_PORT,
    XRAY_CONFIG_PATH,
    XRAY_LOGS_PATH,
    GEO_IP_URL,
    GEO_SITE_URL,
    XRAY_GEO_IP_DATA_PATH,
    XRAY_GEO_SITE_DATA_PATH,
    XRAY_BINARY_PATH,
    XRAY_ARCHIVE_NAME,
    XRAY_DOWNLOAD_URL,
    STYLE_WARN,
    STYLE_REGULAR,
    STYLE_OK,
    STYLE_VALUE,
    EXIT_CONFIGURE_ERROR,
    EXIT_CONFIGURE_HOST_NOT_DETECTED,
    EXIT_CONFIGURE_HOST_REJECTED,
    EXIT_CONFIGURE_NO_RELEASES,
    EXIT_CONFIGURE_VERSION_NOT_FOUND,
)
from app.model.veepeenet import VeePeeNET
from app.model.vless_inbound import (
    VlessInbound,
    StreamSettings as InboundStreamSettings,
    RealitySettings as InboundRealitySettings
)
from app.model.xray import Xray
from app.utils import (
    detect_current_ipv4,
    gen_xray_private_key,
    install_geo_data,
    get_xray_github_releases,
    install_xray_distrib,
    is_xray_service_running,
    get_xray_distrib_version,
    set_value,
)
from app.view import XrayReleasesView


@app.command(help='Configure inbound VLESS Reality Xray service')
@error_handler(default_message='Error during configuration service',
               default_code=EXIT_CONFIGURE_ERROR)
def config(
        host: Annotated[str | None, Option(
            help=('Public interface of server.'
                  ' Using `hostname -i` if not specified.'
                  ' It is recommended to specify manually.'))] = None,
        port: Annotated[int | None, Option(
            help='Inbound port.', show_default=str(VLESS_LISTEN_PORT))] = None,
        reality_host: Annotated[str | None, Option(
            help='Reality host.', show_default=REALITY_HOST)] = None,
        reality_port: Annotated[int | None, Option(
            help='Reality port.', show_default=str(REALITY_PORT))] = None,
        reality_names: Annotated[
            list[str],
            Option(help='Available Reality server names.',
                   show_default='Reality host')] = None,
        name: Annotated[str | None, Option(
            help='Human-readable server name (used after # in client links).')] = None,
        clean: Annotated[bool, Option(help='Override current configuration')] = False,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()
    check_distrib()

    if not XRAY_CONFIG_PATH.exists() or clean:
        if not host:
            host = _detect_host_or_error()
        if clean:
            answer = _confirm_config_rewriting()
            if not answer:
                stdout_console.print(Text('Aborted', STYLE_WARN))
                return
        xray_config = _create_config(
            host,
            port or VLESS_LISTEN_PORT,
            reality_host or REALITY_HOST,
            reality_port or REALITY_PORT,
            reality_names or [reality_host or REALITY_HOST],
            name)
        XRAY_LOGS_PATH.mkdir(parents=True, exist_ok=True)
    else:
        xray_config = load_config(XRAY_CONFIG_PATH)
        _update_config(
            xray_config, host, port, reality_host, reality_port, reality_names, name)

    save_config(xray_config, XRAY_CONFIG_PATH)
    stdout_console.print(Text('VLESS inbound configured', STYLE_REGULAR))


@app.command(help='Update geodata (geoip.dat and geosite.dat) for Xray')
@error_handler(default_message='Error during geodata updating',
               default_code=EXIT_CONFIGURE_ERROR)
def update_geodata() -> None:
    check_root()

    with stdout_console.status(Text('Updating geoip data', STYLE_REGULAR)):
        install_geo_data(GEO_IP_URL, XRAY_GEO_IP_DATA_PATH)
    with stdout_console.status(Text('Updating geosite data', STYLE_REGULAR)):
        install_geo_data(GEO_SITE_URL, XRAY_GEO_SITE_DATA_PATH)
    stdout_console.print(Text('Geoip data', STYLE_OK))


@app.command(help='Update Xray distribution to a selected or latest version')
@error_handler(default_message='Error during Xray distribution update',
               default_code=EXIT_CONFIGURE_ERROR)
def update_xray(
        version: Annotated[
            str | None,
            Option(help='Target version (e.g. v1.8.24 or 1.8.24)')] = None,
        list_versions: Annotated[
            bool,
            Option('--list', help='List available versions and exit')] = False,
        limit: Annotated[
            int,
            Option(help='Number of versions to show with --list')] = 9,
        json: Annotated[
            bool,
            Option('--json', help='Show --list output in JSON format')] = False,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()

    if list_versions:
        _print_available_releases(limit, json)
        return

    selected_version = _select_version(version, limit)
    _install_xray_version(selected_version)


def _print_available_releases(limit: int, json: bool = False) -> None:
    releases = _get_xray_releases(limit)
    if not releases:
        print_error(Text('No Xray releases found', STYLE_REGULAR))
        raise Exit(code=EXIT_CONFIGURE_NO_RELEASES)
    view = XrayReleasesView(releases=releases)
    if json:
        stdout_console.print_json(view.model_dump_json(), indent=2)
    else:
        stdout_console.print(view.rich_repr())


def _select_version(version: str | None, limit: int) -> str:
    if version:
        normalized = version if version.startswith('v') else f'v{version}'
        releases = _get_xray_releases(100)
        if normalized not in releases:
            print_error(Text.assemble(
                ('Version ', STYLE_REGULAR),
                (normalized, STYLE_VALUE),
                (' not found in available releases', STYLE_REGULAR)))
            raise Exit(code=EXIT_CONFIGURE_VERSION_NOT_FOUND)
        return normalized

    releases = _get_xray_releases(limit)
    if not releases:
        print_error('No Xray releases found')
        raise Exit(code=EXIT_CONFIGURE_NO_RELEASES)

    stdout_console.print(XrayReleasesView(releases=releases).rich_repr())

    raw = Prompt.ask(
        Text.assemble(
            ('Select release to install ', STYLE_REGULAR),
            (f'[1-{len(releases)}]', STYLE_VALUE),
            (' (press ', STYLE_REGULAR),
            ('Enter', STYLE_VALUE),
            (' for latest or ', STYLE_REGULAR),
            ('Ctrl+C', STYLE_VALUE),
            (' to cancel', STYLE_REGULAR)),
        choices=[str(i) for i in range(1, len(releases) + 1)],
        default=1,
        show_choices=False,
    )
    return releases[int(raw) - 1]


def _get_xray_releases(limit: int):
    with stdout_console.status(
            Text('Fetching available Xray releases from GitHub', STYLE_REGULAR)):
        return get_xray_github_releases(limit=limit)


def _install_xray_version(selected_version: str) -> None:
    current_version = get_xray_distrib_version()
    if current_version and f'v{current_version}' == selected_version:
        stdout_console.print(Text.assemble(
            ('Xray ', STYLE_REGULAR),
            (selected_version, STYLE_VALUE),
            (' is already installed', STYLE_WARN),
            (', no update required', STYLE_REGULAR)))
        return

    was_running = is_xray_service_running()
    if was_running:
        stop_service()

    with stdout_console.status(Text.assemble(
            ('Downloading Xray ', STYLE_REGULAR),
            (selected_version, STYLE_VALUE))):
        url = urljoin(XRAY_DOWNLOAD_URL, f'{selected_version}/{XRAY_ARCHIVE_NAME}')
        install_xray_distrib(url, XRAY_BINARY_PATH)
    stdout_console.print(Text.assemble(
        Text('Xray ', STYLE_REGULAR),
        (selected_version, STYLE_VALUE),
        (' installed', STYLE_REGULAR)))

    if was_running:
        start_service()


def _detect_host_or_error() -> str:
    host = detect_current_ipv4()
    if not host:
        print_error(Text.assemble(
            ('Cannot auto detect ', STYLE_REGULAR),
            ('public host address', STYLE_VALUE),
            ('. Please specify it manually via ', STYLE_REGULAR),
            ('--host', STYLE_VALUE),
            ('option', STYLE_REGULAR)))
        raise Exit(code=EXIT_CONFIGURE_HOST_NOT_DETECTED)
    detect_host_address_answer = _confirm_host_detection(host)
    if not detect_host_address_answer:
        print_error(Text.assemble(
            ('Please specify it manually via ', STYLE_REGULAR),
            ('--host', STYLE_VALUE),
            ('option', STYLE_REGULAR)))
        raise Exit(code=EXIT_CONFIGURE_HOST_REJECTED)
    return host


def _confirm_host_detection(host: str) -> bool:
    return Confirm.ask(Text.assemble(
        ('Auto detected ', STYLE_REGULAR),
        ('public host address ', STYLE_VALUE),
        ('is ', STYLE_REGULAR),
        (host, STYLE_VALUE),
        (', is it correct?', STYLE_REGULAR)
    ))


def _confirm_config_rewriting() -> bool:
    return Confirm.ask(Text.assemble(
        ('ATTENTION!!! ', STYLE_WARN),
        ('Xray config file ', STYLE_REGULAR),
        (' is already exists', STYLE_WARN),
        (', are you sure to overwrite it?', STYLE_REGULAR)
    ))


def _create_config(host: str, listen_port: int,
                    reality_host: str, reality_port: int, reality_names: list[str],
                    name: str | None = None) -> Xray:
    vless_inbound = VlessInbound(
        listen=VLESS_LISTEN_INTERFACE,
        port=listen_port,
        stream_settings=InboundStreamSettings(
            reality_settings=InboundRealitySettings(
                dest=f'{reality_host}:{reality_port}',
                server_names=reality_names,
                private_key=gen_xray_private_key(),
                short_ids=[])))
    veepeenet = VeePeeNET(host=host, namespace=str(uuid4()), name=name)
    return Xray(veepeenet=veepeenet, inbounds=[vless_inbound])


def _update_config(
        xray_config: Xray,
        host: str | None,
        listen_port: int | None,
        reality_host: str | None,
        reality_port: int | None,
        reality_names: list[str] | None,
        name: str | None = None,
) -> bool:
    vless_inbound = get_vless_inbound(xray_config)

    reality_dest = vless_inbound.stream_settings.reality_settings.dest
    dest_reality_host: str | None = None
    dest_reality_port: int | None = None
    if reality_dest:
        dest_reality_host = reality_host or reality_dest.split(':')[0]
        dest_reality_port = reality_port or int(reality_dest.split(':')[1])

    changed = (
        set_value(xray_config.veepeenet, 'host', host),
        set_value(xray_config.veepeenet, 'name', name),
        set_value(vless_inbound, 'port', listen_port),
        set_value(vless_inbound.stream_settings.reality_settings,
                  'dest', f'{dest_reality_host}:{dest_reality_port}'),
        set_value(
            vless_inbound.stream_settings.reality_settings,
            'server_names', reality_names)
    )
    return any(changed)
