from dataclasses import dataclass
from os import getuid
from pathlib import Path
from sys import getdefaultencoding, exit as sys_exit
from typing import Self
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
from app.model.vless_inbound import Client
from app.model.vless_inbound import VlessInbound, StreamSettings, RealitySettings
from app.model.xray import Xray
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
    start_xray_service,
    remove_duplicates,
    get_new_items,
    get_existing_items,
    get_short_id,
)
from app.view import ServerView, ClientView


@dataclass
class ClientData:
    name: str
    short_id: int
    host: str
    uuid: str

    def __init__(self, name: str, short_id: int, host: str, uuid: str = '') -> None:
        self.name = name
        self.short_id = short_id
        self.host = host
        self.uuid = uuid if uuid else str(uuid4())

    @classmethod
    def from_model(cls, client: Client, host: str) -> Self:
        name = '.'.join(client.email.split('@')[0].split('.')[:-1])
        uuid = client.id
        short_id = int(client.email.split('@')[0].split('.')[-1])
        return ClientData(name=name, short_id=short_id, host=host, uuid=uuid)

    def to_model(self) -> Client:
        return Client(
            id=self.uuid,
            email=f'{self.name}.{self.short_id:04}@{self.host}'
        )


def check_and_install(
        bin_path: Path = XRAY_BINARY_PATH,
        unit_path: Path = XRAY_SERVICE_UNIT_PATH,
        archive_name: str = XRAY_ARCHIVE_NAME
) -> None:
    if getuid() != 0:
        print('Xray configuration must be run as root')
        sys_exit(-1)
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


def exit_if_xray_config_not_found(xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    if not xray_config_path.exists():
        print('Xray config file not found, please run the `config` command first')
        sys_exit(-1)


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
        stream_settings=StreamSettings(
            reality_settings=RealitySettings(
                dest=f'{reality_host}:{reality_port}',
                server_names=[reality_host],
                private_key=gen_xray_private_key(),
                short_ids=[])))
    return Xray(inbounds=[vless_inbound])


def load_config(xray_config_path: Path) -> Xray:
    try:
        config_content = xray_config_path.read_text(getdefaultencoding())
    except FileNotFoundError:
        print('Config file not found')
        raise
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
        clients=client_views)


def stop() -> None:
    if not is_xray_service_running():
        print('Xray service is not running')
        return
    stop_xray_service()
    print('Xray service stopped')


def start() -> None:
    if is_xray_service_running():
        print('Xray service is already running')
        return
    start_xray_service()
    print('Xray service started')


def add_clients(names: list[str], xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    xray_config = load_config(xray_config_path)
    settings = xray_config.inbounds[0].settings
    host = xray_config.inbounds[0].listen
    reality_settings = xray_config.inbounds[0].stream_settings.reality_settings

    existing_clients_data = [ClientData.from_model(client, host) for client in settings.clients]
    existing_names = [client_data.name for client_data in existing_clients_data]
    new_names = get_new_items(existing_names, remove_duplicates(names))
    already_existing_names = get_existing_items(existing_names, names)

    if already_existing_names:
        print('These clients already exist and will be skipped:',
              ', '.join(already_existing_names))
    if not new_names:
        print('No new clients found')
        return

    existing_short_ids = [client_data.short_id for client_data in existing_clients_data]
    for name in new_names:
        short_id = get_short_id(existing_short_ids)
        existing_short_ids.append(short_id)
        new_client_data = ClientData(name=name, short_id=short_id, host=host)
        existing_clients_data.append(new_client_data)

    settings.clients = [client_data.to_model() for client_data in existing_clients_data]
    reality_settings.short_ids = [f'{short_id:04}' for short_id in existing_short_ids]

    write_text_file(
        xray_config_path,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    print('Added new clients:', ', '.join(new_names))


def remove_clients(names: list[str], xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    xray_config = load_config(xray_config_path)
    clients = xray_config.inbounds[0].settings.clients
    host = xray_config.inbounds[0].listen
    reality_settings = xray_config.inbounds[0].stream_settings.reality_settings
    settings = xray_config.inbounds[0].settings

    existing_clients_data = [ClientData.from_model(client, host) for client in clients]
    existing_names = [client_data.name for client_data in existing_clients_data]
    removable_names = get_existing_items(existing_names, remove_duplicates(names))
    unknown_names = get_new_items(existing_names, names)

    if unknown_names:
        print('These clients are unknown and will be skipped:',
              ', '.join(unknown_names))
    if not removable_names:
        print('No clients found to remove')
        return

    existing_short_ids = [client_data.short_id for client_data in existing_clients_data]
    for existing_client_data in existing_clients_data:
        if existing_client_data.name in removable_names:
            existing_clients_data.remove(existing_client_data)
            existing_short_ids.remove(existing_client_data.short_id)

    settings.clients = [client_data.to_model() for client_data in existing_clients_data]
    reality_settings.short_ids = [f'{short_id:04}' for short_id in existing_short_ids]

    write_text_file(
        xray_config_path,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    print('Removed clients:', ', '.join(removable_names))
