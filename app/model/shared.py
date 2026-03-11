from typing import Literal, Any

from pydantic import Field

from app.defaults import XRAY_ACCESS_LOG_PATH, XRAY_ERROR_LOG_PATH
from app.model.base import XrayModel


class Log(XrayModel):
    access: str = Field(default=str(XRAY_ACCESS_LOG_PATH))
    error: str = Field(default=str(XRAY_ERROR_LOG_PATH))
    loglevel: Literal['off', 'error', 'info', 'warning', 'debug'] = Field(default='off')
    dns_log: bool = Field(default=False)


class Dns(XrayModel):
    servers: list[str] | list[dict[str, Any]] | None = Field(
        default_factory=lambda: ['1.1.1.1', '1.0.0.1', '8.8.8.8', '8.8.4.4'])


class DnsOutbound(XrayModel):
    class Settings(XrayModel):
        network: Literal['tcp', 'udp'] | None = Field(default=None)
        address: str | None = Field(default=None)
        port: int | None = Field(default=None)
        blockTypes: list[int] | None = Field(default=None, alias='blockTypes')
        non_ip_query: Literal['skip', 'drop', 'reject'] | None = Field(
            default='skip', alias='nonIPQuery')

    tag: str | None = 'dns'
    protocol: Literal['dns'] = 'dns'
    settings: Settings | None = Field(default_factory=Settings)


class FreedomOutbound(XrayModel):
    tag: str | None = 'direct'
    protocol: Literal['freedom'] = 'freedom'


class BlackholeOutbound(XrayModel):
    tag: str | None = 'blackhole'
    protocol: Literal['blackhole'] = 'blackhole'
