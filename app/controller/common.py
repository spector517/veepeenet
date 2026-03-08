from dataclasses import dataclass
from functools import wraps
from os import getuid
from pathlib import Path
from typing import Self, Callable, Any
from urllib.parse import urljoin
from uuid import uuid4, uuid5, UUID

from typer import echo, Exit

from app.defaults import (
    XRAY_BINARY_PATH,
    XRAY_SERVICE_UNIT_PATH,
    XRAY_ARCHIVE_NAME,
    XRAY_DOWNLOAD_URL,
    XRAY_ACCESS_LOG_PATH,
    XRAY_ERROR_LOG_PATH,
    XRAY_CONFIG_PATH
)
from app.model.vless_inbound import Client, VlessInbound
from app.model.xray import Xray
from app.model.routing import Rule
from app.model.types import RuleProtocolType
from app.utils import (
    detect_veepeenet_versions,
    get_xray_distrib_version,
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
    short_id: str
    host: str
    uuid: UUID

    def __init__(
            self, name: str,
            short_id: str,
            host: str,
            namespace: UUID | None = None,
            uuid: UUID | None = None) -> None:
        self.name = name
        self.short_id = short_id
        self.host = host
        if uuid:
            self.uuid = uuid
        elif namespace:
            self.uuid = uuid5(namespace, name)
        else:
            self.uuid = uuid4()

    @classmethod
    def from_model(cls, client: Client, host: str) -> Self:
        name = '.'.join(client.email.split('@')[0].split('.')[:-1])
        uuid = UUID(client.id)
        short_id = client.email.split('@')[0].split('.')[-1]
        return ClientData(name=name, short_id=short_id, host=host, uuid=uuid)

    def to_model(self) -> Client:
        return Client(
            id=str(self.uuid),
            email=f'{self.name}.{self.short_id}@{self.host}'
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

def error_handler(
        default_message: str | None = None, default_code: int = -1) -> Callable[..., Any]:

    def wrapper_func(func: Callable[..., Any]) -> Callable[..., Any]:

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any | None:
            try:
                return func(*args, **kwargs)
            except Exit:
                raise
            except BaseException as e:
                if '_debug' in kwargs and kwargs['_debug']:
                    raise
                echo(f'{default_message or "Unknown error"}: {e}', err=True)
                raise Exit(code=default_code) from e

        return wrapper

    return wrapper_func


def check_distrib(
        bin_path: Path = XRAY_BINARY_PATH,
        unit_path: Path = XRAY_SERVICE_UNIT_PATH,
        archive_name: str = XRAY_ARCHIVE_NAME,
) -> None:
    versions = detect_veepeenet_versions()
    was_stopped = False

    if not get_xray_distrib_version():
        echo('Xray distribution is not installed. Will install it now...')
        if is_xray_service_running():
            stop_xray_service()
            echo('Stopped running Xray service')
            was_stopped = True
        url = urljoin(XRAY_DOWNLOAD_URL, f'{versions.xray_version}/{archive_name}')
        install_xray_distrib(url, bin_path)
        write_text_file(XRAY_ACCESS_LOG_PATH, "")
        write_text_file(XRAY_ERROR_LOG_PATH, "")
        echo('Xray distribution installed')

    if not is_xray_service_installed(unit_path):
        echo('Required Xray service is not installed. Will install it now...')
        if is_xray_service_running():
            stop_xray_service()
            echo('Stopped running Xray service')
            was_stopped = True
        install_xray_service(unit_path)
        echo('Xray service installed')
        if is_xray_service_enabled():
            disable_xray_service()
            enable_xray_service()

    if was_stopped:
        start_xray_service()
        echo('Started Xray service')


def check_root() -> None:
    if getuid() != 0:
        echo('This command must be run as root', err=True)
        raise Exit(code=1)


def check_xray_config(xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    if not xray_config_path.exists():
        echo('Xray config file not found, please run the `xrayctl config` command first',
                   err=True)
        raise Exit(code=2)


def load_config(xray_config_path: Path) -> Xray:
    try:
        config_content = xray_config_path.read_text('utf-8')
    except FileNotFoundError:
        echo('Config file not found', err=True)
        raise
    return Xray.model_validate_json(config_content, by_alias=True)


def get_vless_inbound(xray_config: Xray) -> VlessInbound:
    inbound = xray_config.get_vless_inbound()
    if inbound:
        return inbound
    raise ValueError('VLESS inbound not found in config')
