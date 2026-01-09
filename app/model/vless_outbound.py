from typing import Literal

from pydantic import Field

from app.model.base import XrayModel


class Settings(XrayModel):
    address: str
    port: int = Field(default=443)
    id: str
    encryption: Literal['none'] = 'none'
    flow: Literal['xtls-rprx-vision'] = 'xtls-rprx-vision'


class RealitySettings(XrayModel):
    server_name: str
    fingerprint: Literal['chrome'] = 'chrome'
    public_key: str
    short_id: str
    spider_x: str


class StreamSettings(XrayModel):
    security: Literal['reality'] = 'reality'
    reality_settings: RealitySettings


class VlessOutbound(XrayModel):
    tag: str
    protocol: Literal['vless'] = 'vless'
    settings: Settings
    stream_settings: StreamSettings
