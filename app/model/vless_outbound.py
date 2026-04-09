from typing import Literal

from pydantic import Field

from app.model.base import XrayModel
from app.model.types import FingerprintType


class Settings(XrayModel):
    address: str
    port: int
    id: str
    encryption: Literal['none'] = 'none'
    flow: Literal['xtls-rprx-vision'] = 'xtls-rprx-vision'


class RealitySettings(XrayModel):
    server_name: str
    fingerprint: FingerprintType
    password: str
    short_id: str
    spider_x: str = Field(default_factory=lambda: '/')


class StreamSettings(XrayModel):
    security: Literal['reality'] = 'reality'
    reality_settings: RealitySettings


class VlessOutbound(XrayModel):
    tag: str | None = Field(default=None)
    send_through: str | None = Field(default=None)
    protocol: Literal['vless'] = 'vless'
    settings: Settings
    stream_settings: StreamSettings
