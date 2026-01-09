from typing import Literal

from pydantic import Field

from app.model.base import XrayModel


class Client(XrayModel):
    email: str
    id: str
    flow: Literal['xtls-rprx-vision'] = 'xtls-rprx-vision'


class RealitySettings(XrayModel):
    dest: str
    server_names: list[str]
    private_key: str
    short_ids: list[str]


class Settings(XrayModel):
    clients: list[Client] = Field(default_factory=list)
    decryption: Literal['none'] = 'none'


class StreamSettings(XrayModel):
    reality_settings: RealitySettings
    security: Literal['reality'] = 'reality'


class Sniffing(XrayModel):
    enabled: bool = Field(default=False)
    route_only: bool = Field(default=True)
    dest_override: list[str] = Field(default=['http', 'tls', 'quic'])


class VlessInbound(XrayModel):
    listen: str
    port: int
    protocol: Literal['vless'] = 'vless'
    tag: str = Field(default='vless-inbound')
    settings: Settings = Field(default=Settings())
    stream_settings: StreamSettings
    sniffing: Sniffing = Field(default=Sniffing())
