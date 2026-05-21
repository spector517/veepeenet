from typing import Annotated, Any, Self
from uuid import uuid4

from pydantic import Field, model_serializer, model_validator

from app.defaults import VLESS_LISTEN_INTERFACE
from app.model.base import XrayModel
from app.model.routing import Routing
from app.model.shared import (
    Log,
    Dns,
    FreedomOutbound,
    BlackholeOutbound,
    DnsOutbound,
    ApiConfig,
    Policy,
    StatsConfig
)
from app.model.veepeenet import VeePeeNet
from app.model.vless_inbound import VlessInbound
from app.model.vless_outbound import VlessOutbound

Outbound = Annotated[
    VlessOutbound | FreedomOutbound | BlackholeOutbound | DnsOutbound,
    Field(discriminator='protocol')]

_REQUIRED_OUTBOUNDS: list[type] = [FreedomOutbound, BlackholeOutbound, DnsOutbound]


class Xray(XrayModel):
    veepeenet: VeePeeNet | None = Field(default=None)
    log: Log = Field(default_factory=Log)
    dns: Dns | None = Field(default=None)
    api: ApiConfig = Field(default_factory=ApiConfig)
    policy: Policy = Field(default_factory=Policy)
    stats: StatsConfig = Field(default_factory=StatsConfig)
    inbounds: list[VlessInbound | dict[str, Any]] = Field(default_factory=lambda: [])
    routing: Routing | None = Field(default=None)
    outbounds: list[Outbound | dict[str, Any]] = Field(
        default_factory=lambda: [FreedomOutbound(), BlackholeOutbound(), DnsOutbound()])

    def get_vless_inbound(self) -> VlessInbound | None:
        for inbound in self.inbounds or []:
            if isinstance(inbound, VlessInbound):
                return inbound
        return None

    @model_serializer(mode='wrap')
    def _ensure_required_outbounds(self, handler: Any) -> Any:
        outbounds = self.outbounds or []
        existing_types = [type(out) for out in outbounds if not isinstance(out, dict)]
        for required_type in _REQUIRED_OUTBOUNDS:
            if required_type not in existing_types:
                outbounds = outbounds + [required_type()]
        self.outbounds = outbounds
        return handler(self)

    @model_validator(mode='after')
    def _fill_veepeenet(self) -> Self:
        if self.veepeenet:
            return self
        inbound = self.get_vless_inbound()
        if not inbound:
            raise ValueError('Vless inbound is required to auto fill VeePeeNET config')
        self.veepeenet = VeePeeNet(
            host=inbound.listen or VLESS_LISTEN_INTERFACE,
            namespace=str(uuid4()))
        return self
