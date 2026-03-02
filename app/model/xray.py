from typing import Annotated, Any

from pydantic import Field, model_serializer

from app.model.base import XrayModel
from app.model.routing import Routing
from app.model.shared import Log, Dns, FreedomOutbound, BlackholeOutbound, DnsOutbound
from app.model.vless_inbound import VlessInbound
from app.model.vless_outbound import VlessOutbound

Outbound = Annotated[
    VlessOutbound | FreedomOutbound | BlackholeOutbound | DnsOutbound,
    Field(discriminator='protocol')]

_REQUIRED_OUTBOUNDS: list[type] = [FreedomOutbound, BlackholeOutbound, DnsOutbound]


class Xray(XrayModel):
    log: Log | None = Field(default_factory=Log)
    dns: Dns | None = Field(default=None)
    inbounds: list[VlessInbound] | list[dict] | None = Field(default=None)
    routing: Routing | None = Field(default=None)
    outbounds: list[Outbound] | list[dict] | None = Field(
        default_factory=lambda: [FreedomOutbound(), BlackholeOutbound(), DnsOutbound()])

    @model_serializer(mode='wrap')
    def ensure_required_outbounds(self, handler: Any) -> Any:
        outbounds = list(self.outbounds) if self.outbounds is not None else []
        existing_types = {type(out) for out in outbounds if not isinstance(out, dict)}
        for required_type in _REQUIRED_OUTBOUNDS:
            if required_type not in existing_types:
                outbounds = outbounds + [required_type()]
        self.outbounds = outbounds
        return handler(self)
