from typing import Literal

from pydantic import Field

from app.model.base import XrayModel
from app.defaults import XRAY_ACCESS_LOG_PATH, XRAY_ERROR_LOG_PATH


class Log(XrayModel):
    access: str = Field(default=str(XRAY_ACCESS_LOG_PATH))
    error: str = Field(default=str(XRAY_ERROR_LOG_PATH))
    loglevel: Literal['off', 'error', 'info', 'debug'] = Field(default='info')
    dns_log: bool = Field(default=False)


class Dns(XrayModel):
    servers: list[str] = Field(
        default_factory=lambda: ['1.1.1.1', '1.0.0.1', '8.8.8.8', '8.8.4.4'])


class DnsOutbound(XrayModel):
    class Settings(XrayModel):
        network: Literal['tcp'] = 'tcp'
        non_ip_query: Literal['skip'] = Field(default='skip', alias='nonIPQuery')

    protocol: Literal['dns'] = 'dns'
    settings: Settings = Field(default_factory=Settings)
    tag: Literal['dns'] = 'dns'


class FreedomOutbound(XrayModel):
    tag: Literal['direct', 'direct-outbound'] = 'direct'
    protocol: Literal['freedom'] = 'freedom'


class BlackholeOutbound(XrayModel):
    tag: Literal['blackhole', 'blackhole-outbound'] = 'blackhole'
    protocol: Literal['blackhole'] = 'blackhole'
