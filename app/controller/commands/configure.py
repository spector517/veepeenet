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
    XRAY_BINARY_PATH,
    XRAY_ARCHIVE_NAME,
    XRAY_DOWNLOAD_URL,
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
    write_text_file,
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
@error_handler(default_message='Error during configuration service', default_code=10)
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
                stdout_console.print('Aborted')
                return
        xray_config = _create_config(
            host,
            port or VLESS_LISTEN_PORT,
            reality_host or REALITY_HOST,
            reality_port or REALITY_PORT,
            reality_names or [reality_host])
    else:
        xray_config = load_config(XRAY_CONFIG_PATH)
        _update_config(
            xray_config, host, port, reality_host, reality_port, reality_names)

    write_text_file(
        XRAY_CONFIG_PATH,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    stdout_console.print('Successfully configured VLESS inbound')


@app.command(help='Update geodata (geoip.dat and geosite.dat) for Xray')
@error_handler(default_message='Error during geodata updating', default_code=10)
def update_geodata() -> None:
    check_root()

    with stdout_console.status('Updating geoip data'):
        install_geo_data(GEO_IP_URL, XRAY_GEO_IP_DATA_PATH)
    with stdout_console.status('Updating geosite data'):
        install_geo_data(GEO_SITE_URL, XRAY_GEO_SITE_DATA_PATH)
    stdout_console.print('Geodata updated')


@app.command(help='Update Xray distribution to a selected or latest version')
@error_handler(default_message='Error during Xray distribution update', default_code=10)
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
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    check_root()

    if list_versions:
        _print_available_releases(limit)
        return

    selected_version = _select_version(version, limit)
    _install_xray_version(selected_version)


def _print_available_releases(limit: int) -> None:
    with stdout_console.status('Fetching available Xray releases from GitHub'):
        releases = get_xray_github_releases(limit=limit)
    if not releases:
        print_error('No Xray releases found')
        raise Exit(code=13)
    stdout_console.print(XrayReleasesView(releases=releases).rich_repr())


def _select_version(version: str | None, limit: int) -> str:
    if version:
        normalized = version if version.startswith('v') else f'v{version}'
        with stdout_console.status('Fetching available Xray releases from GitHub'):
            releases = get_xray_github_releases(limit=100)
        if normalized not in releases:
            print_error(Text.assemble(
                'Version ', (normalized, 'bold yellow'), ' not found in available releases'))
            raise Exit(code=14)
        return normalized

    with stdout_console.status('Fetching available Xray releases from GitHub'):
        releases = get_xray_github_releases(limit=limit)
    if not releases:
        print_error('No Xray releases found')
        raise Exit(code=13)

    stdout_console.print(XrayReleasesView(releases=releases).rich_repr())

    raw = Prompt.ask(
        f'Select release to install [1-{len(releases)}] '
        f'(press Enter for latest or Ctrl+C to cancel)',
        choices=[str(i) for i in range(1, len(releases) + 1)],
        default=1,
        show_choices=False,
    )

    choice = int(raw)
    if choice < 1 or choice > len(releases):
        raise ValueError
    return releases[choice - 1]


def _install_xray_version(selected_version: str) -> None:
    current_version = get_xray_distrib_version()
    if current_version and f'v{current_version}' == selected_version:
        stdout_console.print(Text.assemble(
            'Xray ',
            (selected_version, 'bold cyan'),
            ' is already installed, no update required'))
        return

    was_running = is_xray_service_running()
    if was_running:
        stop_service()

    with stdout_console.status(f'Downloading Xray {selected_version}'):
        url = urljoin(XRAY_DOWNLOAD_URL, f'{selected_version}/{XRAY_ARCHIVE_NAME}')
        install_xray_distrib(url, XRAY_BINARY_PATH)
    stdout_console.print(Text.assemble(
        'Xray ',
        (selected_version, 'bold cyan'),
        ' installed successfully'))

    if was_running:
        start_service()


def _detect_host_or_error() -> str:
    host = detect_current_ipv4()
    if not host:
        print_error(Text.assemble(
            'Cannot auto detect ',
            ('public host address', 'bold'),
            '. Please specify it manually via --host option'))
        raise Exit(code=11)
    detect_host_address_answer = _confirm_host_detection(host)
    if not detect_host_address_answer:
        print_error(Text.assemble(
            'Please specify ',
            ('public host address', 'bold'),
             'manually via --host option'))
        raise Exit(code=12)
    return host


def _confirm_host_detection(host: str) -> bool:
    return Confirm.ask(Text.assemble(
        'Auto detected ',
        ('public host address ', 'bold'),
        'is ',
        (host, 'bold'),
        ', is it correct?'
    ))


def _confirm_config_rewriting() -> bool:
    return Confirm.ask(Text.assemble(
        ('ATTENTION!!! ', 'yellow'),
        'Xray config file already exists, are you sure to overwrite it?'
    ))


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
        host: str | None,
        listen_port: int | None,
        reality_host: str | None,
        reality_port: int | None,
        reality_names: list[str] | None
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
        set_value(vless_inbound, 'port', listen_port),
        set_value(vless_inbound.stream_settings.reality_settings,
                  'dest', f'{dest_reality_host}:{dest_reality_port}'),
        set_value(
            vless_inbound.stream_settings.reality_settings,
            'server_names', reality_names)
    )
    return any(changed)
