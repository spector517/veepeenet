from dataclasses import dataclass
from functools import wraps
from os import getuid
from pathlib import Path
from sys import exit as sys_exit, getdefaultencoding
from typing import Self, Callable, Any
from urllib.parse import urljoin
from uuid import uuid4

from app.defaults import (
    XRAY_BINARY_PATH,
    XRAY_SERVICE_UNIT_PATH,
    XRAY_ARCHIVE_NAME,
    XRAY_DOWNLOAD_URL,
    XRAY_ACCESS_LOG_PATH,
    XRAY_ERROR_LOG_PATH,
    XRAY_CONFIG_PATH
)
from app.model.vless_inbound import Client
from app.model.xray import Xray
from app.model.routing import Rule
from app.model.types import RuleProtocolType
from app.utils import (
    detect_veepeenet_versions,
    is_xray_distrib_installed,
    is_xray_service_running,
    stop_xray_service,
    install_xray_distrib,
    write_text_file,
    is_xray_service_installed,
    install_xray_service,
    is_xray_service_enabled,
    disable_xray_service,
    enable_xray_service,
    start_xray_service
)


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


@dataclass
class RuleData:
    name: str
    outbound_name: str
    protocols: list[RuleProtocolType] | None
    ports: str | None
    domains: list[str] | None
    ips: list[str] | None
    priority: int

    @classmethod
    def from_model(cls, rule: Rule, number: int = 0) -> Self:
        split_name = rule.tag.split('.')
        try:
            priority = int(split_name[-1])
            name = '.'.join(split_name[:-1])
        except ValueError:
            priority = (number + 1) * 10
            name = rule.tag
        return RuleData(name=name, outbound_name=rule.outbound_tag, protocols=rule.protocol,
                        ports=rule.port, domains=rule.domain, ips=rule.ip, priority=priority)

    def to_model(self) -> Rule:
        return Rule(
            tag=f'{self.name}.{self.priority}',
            outbound_tag=self.outbound_name,
            protocol=self.protocols,
            port=self.ports,
            domain=self.domains,
            ip=self.ips
        )

def error_handler(default_message: str | None = None) -> Callable[..., ...]:

    def wrapper_func(func: Callable[..., ...]) -> Callable[..., ...]:

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any | None:
            try:
                return func(*args, **kwargs)
            except Exception as e:  # pylint: disable=broad-exception-caught
                if '_debug' in kwargs and kwargs['_debug']:
                    raise
                print(f'{default_message or "Unknown error"}: {e}')
                return None

        return wrapper

    return wrapper_func


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


def load_config(xray_config_path: Path) -> Xray:
    try:
        config_content = xray_config_path.read_text(getdefaultencoding())
    except FileNotFoundError:
        print('Config file not found')
        raise
    return Xray.model_validate_json(config_content, by_alias=True)
