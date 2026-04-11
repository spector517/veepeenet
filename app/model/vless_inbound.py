from typing import Literal

from pydantic import Field

from app.model.base import XrayModel


class Client(XrayModel):
    email: str | None = Field(default=None)
    id: str
    flow: Literal['xtls-rprx-vision', 'xtls-rprx-vision-udp443'] = 'xtls-rprx-vision'


class RealitySettings(XrayModel):
    dest: str
    server_names: list[str]
    private_key: str
    short_ids: list[str]


class Settings(XrayModel):
    clients: list[Client] | None = Field(default_factory=lambda: [])
    decryption: Literal['none'] = 'none'


class StreamSettings(XrayModel):
    reality_settings: RealitySettings
    security: Literal['reality'] = 'reality'


class Sniffing(XrayModel):
    enabled: bool = Field(default=False)
    route_only: bool = Field(default=True)
    dest_override: list[str] | None = Field(
        default_factory=lambda: ['http', 'tls', 'quic'])


class VlessInbound(XrayModel):
    tag: str | None = Field(default='vless-inbound')
    listen: str | None = Field(default=None)
    port: int | str
    protocol: Literal['vless'] = 'vless'
    settings: Settings = Field(default_factory=Settings)
    stream_settings: StreamSettings
    sniffing: Sniffing = Field(default_factory=Sniffing)
