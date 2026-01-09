from sys import getdefaultencoding, exit
from os.path import exists
from os import getuid
from urllib.parse import urljoin
from uuid import uuid4

from app.defaults import (
    XRAY_DOWNLOAD_URL,
    XRAY_BINARY_PATH,
    XRAY_SERVICE_UNIT_PATH,
    XRAY_ARCHIVE_NAME,
    XRAY_CONFIG_PATH,
    XRAY_ACCESS_LOG_PATH,
    XRAY_ERROR_LOG_PATH
)
from app.model.vless_inbound import VlessInbound, StreamSettings, RealitySettings
from app.model.xray import Xray
from app.model.vless_inbound import Client
from app.utils import (
    gen_xray_private_key,
    write_text_file,
    detect_current_ipv4,
    is_xray_distrib_installed,
    is_xray_service_installed,
    is_xray_service_running,
    stop_xray_service,
    is_xray_service_enabled,
    enable_xray_service,
    disable_xray_service,
    get_vless_client_url,
    install_xray_distrib,
    install_xray_service,
    detect_veepeenet_versions,
    start_xray_service
)
from app.view import ServerView, ClientView


def check_and_prepare(
        bin_path: str = XRAY_BINARY_PATH,
        unit_path: str = XRAY_SERVICE_UNIT_PATH,
        archive_name: str = XRAY_ARCHIVE_NAME
) -> None:
    if getuid() != 0:
        print('Xray configuration must be run as root')
        exit(-1)
    versions = detect_veepeenet_versions()
    was_stopped = False

    if not is_xray_distrib_installed(versions.xray_version):
        print('Required Xray distribution is not installed. Will install it now...')
        if is_xray_service_running():
            stop_xray_service()
            print('Stopped running Xray service')
            was_stopped = True
        url = urljoin(XRAY_DOWNLOAD_URL, f'{versions.xray_version}/{archive_name}')
        install_xray_distrib(url, bin_path)
        write_text_file(XRAY_ACCESS_LOG_PATH, "")
        write_text_file(XRAY_ERROR_LOG_PATH, "")
        print('Xray distribution installed')

    if not is_xray_service_installed(unit_path):
        print('Required Xray service is not installed. Will install it now...')
        if is_xray_service_running():
            stop_xray_service()
            print('Stopped running Xray service')
            was_stopped = True
        install_xray_service(unit_path)
        print('Xray service installed')
        if is_xray_service_enabled():
            disable_xray_service()
            enable_xray_service()

    if was_stopped:
        start_xray_service()
        print('Started Xray service')


def config(
        listen: str,
        listen_port: int,
        reality_host: str,
        reality_port: int,
        clean: bool,
        xray_config_path: str = XRAY_CONFIG_PATH
) -> None:
    if not listen:
        listen = detect_current_ipv4()
    if not listen:
        raise RuntimeError('Cannot auto detect public host address.'
                           ' Please specify it manually via --host option')
    detect_host_address_answer = confirm_host_detection(listen)
    if not detect_host_address_answer:
        raise RuntimeError('Please specify it manually via --host option')

    if not exists(xray_config_path) or clean:
        if clean:
            answer = confirm_config_rewriting()
            if not answer:
                print('Aborted')
                exit(0)

        xray_config = create_config(listen, listen_port, reality_host, reality_port)
    else:
        xray_config = load_config(XRAY_CONFIG_PATH)
        xray_config = update_config(xray_config, listen, listen_port, reality_host, reality_port)

    write_text_file(
        xray_config_path,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    if is_xray_service_running():
        stop_xray_service()
        start_xray_service()
        print('Xray service restarted')


def confirm_host_detection(host: str) -> bool:
    answer = input(f'Auto detected public host address is {host}, is it correct? (y/N): ')
    return answer.lower() == 'y'


def confirm_config_rewriting() -> bool:
    answer = input('ATTENTION!!! Xray config file already exists, are you sure to overwrite it? (y/N): ')
    return answer.lower() == 'y'


def create_config(listen: str, listen_port: int, reality_host: str, reality_port: int) -> Xray:
    vless_inbound = VlessInbound(
        listen=listen,
        port=listen_port,
        stream_settings=StreamSettings(
            reality_settings=RealitySettings(
                dest=f'{reality_host}:{reality_port}',
                server_names=[reality_host],
                private_key=gen_xray_private_key(),
                short_ids=[])))
    return Xray(inbounds=[vless_inbound])


def load_config(xray_config_path: str) -> Xray:
    if not exists(xray_config_path):
        raise FileNotFoundError(f'Config file not found: {xray_config_path}')
    with open(xray_config_path, 'rt', encoding=getdefaultencoding()) as config_file:
        config_content = config_file.read()
    return Xray.model_validate_json(config_content, by_alias=True)


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


def status() -> ServerView:
    if not exists(XRAY_CONFIG_PATH):
        print('Xray config file not found, please run the `init` command first')
        exit(-1)
    xray_config = load_config(XRAY_CONFIG_PATH)
    versions = detect_veepeenet_versions()

    client_views: list[ClientView] = []
    for client in xray_config.inbounds[0].settings.clients:
        client_name = client.email.split('@')[0]
        client_url = get_vless_client_url(client_name, xray_config)
        client_views.append(ClientView(
            name=client_name,
            url=client_url))

    return ServerView(
        veepeenet_version=versions.veepeenet_version,
        veepeenet_build=versions.veepeenet_build,
        xray_version=versions.xray_version,
        server_status='Running' if is_xray_service_running() else 'Stopped',
        server_host=xray_config.inbounds[0].listen,
        server_port=xray_config.inbounds[0].port,
        reality_address=xray_config.inbounds[0].stream_settings.reality_settings.dest,
        clients=client_views)


def stop(xray_config_path: str = XRAY_CONFIG_PATH) -> None:
    if not exists(xray_config_path):
        print('Xray config file not found, please run the `init` command first')
        exit(-1)
    if not is_xray_service_running():
        print('Xray service is not running')
        return
    stop_xray_service()
    print('Xray service stopped')


def start(xray_config_path: str = XRAY_CONFIG_PATH) -> None:
    if not exists(xray_config_path):
        print('Xray config file not found, please run the `init` command first')
        exit(-1)
    if is_xray_service_running():
        print('Xray service is already running')
        return
    start_xray_service()
    print('Xray service started')


def add_clients(names: list[str], xray_config_path: str = XRAY_CONFIG_PATH) -> None:
    if not exists(xray_config_path):
        print('Xray config file not found, please run the `init` command first')
        exit(-1)

    xray_config = load_config(XRAY_CONFIG_PATH)
    clients = xray_config.inbounds[0].settings.clients
    host = xray_config.inbounds[0].listen
    short_ids = xray_config.inbounds[0].stream_settings.reality_settings.short_ids

    existing_names = set([client.email.split('@')[0] for client in clients])
    new_names = set(names) - existing_names
    already_existing_names = set(names) & existing_names

    if already_existing_names:
        print('These clients already exist and will be skipped:',
              ', '.join(already_existing_names))

    if not new_names:
        print('No new clients found')
        return
    new_clients_string = str()
    for name in new_names:
        clients.append(Client(id=str(uuid4()), email=f'{name}@{host}'))
        short_ids.append(f'{len(clients):04}')
        new_clients_string += f'\t{repr(ClientView(
            name=name, url=get_vless_client_url(name, xray_config)))}\n'

    write_text_file(
        xray_config_path,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    print('Added new clients:', new_clients_string, sep='\n', end='')
    if is_xray_service_running():
        stop_xray_service()
        start_xray_service()
        print('Xray service restarted')
