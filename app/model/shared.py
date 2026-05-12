from typing import Literal

from pydantic import Field, field_validator

from app.defaults import XRAY_ERROR_LOG_PATH, XRAY_API_HOST, XRAY_API_PORT
from app.model.base import XrayModel

XrayLogLevel = Literal['none', 'off', 'error', 'info', 'warning', 'debug']


class Log(XrayModel):
    access: str = Field(default='none')
    error: str = Field(default=str(XRAY_ERROR_LOG_PATH))
    loglevel: XrayLogLevel = Field(default='warning')
    dns_log: bool = Field(default=False)

    @field_validator('loglevel', mode='before')
    @classmethod
    def _normalize_loglevel(cls, v: str) -> str:
        return 'none' if v == 'off' else v


class DnsServer(XrayModel):
    address: str
    port: int | None = Field(default=None)
    domains: list[str] | None = Field(default=None)
    expect_ips: list[str] | None = Field(default=None)
    skip_fallback: bool | None = Field(default=None)


class Dns(XrayModel):
    servers: list[str | DnsServer] | None = Field(
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


class PolicyLevel(XrayModel):
    stats_user_uplink: bool = True
    stats_user_downlink: bool = True


class SystemPolicy(XrayModel):
    stats_inbound_uplink: bool = True
    stats_inbound_downlink: bool = True
    stats_outbound_uplink: bool = True
    stats_outbound_downlink: bool = True


class Policy(XrayModel):
    levels: dict[str, PolicyLevel] = Field(default_factory=lambda: {'0': PolicyLevel()})
    system: SystemPolicy = Field(default_factory=SystemPolicy)


class ApiConfig(XrayModel):
    tag: str = 'api'
    listen: str = Field(default_factory=lambda: f'{XRAY_API_HOST}:{XRAY_API_PORT}')
    services: list[str] = Field(default_factory=lambda: ['StatsService'])



class StatsConfig(XrayModel):
    pass
