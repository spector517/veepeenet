from typing import Annotated

from pydantic import Field

from app.model.base import XrayModel
from app.model.routing import Routing
from app.model.shared import Log, Dns, FreedomOutbound, BlackholeOutbound, DnsOutbound
from app.model.vless_inbound import VlessInbound
from app.model.vless_outbound import VlessOutbound

Outbound = Annotated[
    VlessOutbound | FreedomOutbound | BlackholeOutbound | DnsOutbound,
    Field(discriminator='protocol')]


class Xray(XrayModel):
    log: Log | None = Field(default_factory=Log)
    dns: Dns | None = Field(default=None)
    inbounds: list[VlessInbound] | list[dict] | None = Field(default=None)
    routing: Routing | None = Field(default=None)
    outbounds: list[Outbound] | list[dict] | None = Field(
        default_factory=lambda: [FreedomOutbound(), BlackholeOutbound(), DnsOutbound()])
