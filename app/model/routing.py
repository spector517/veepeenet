from pydantic import Field

from app.model.base import XrayModel
from app.model.types import RoutingDomainStrategyType
from app.model.types import RuleProtocolType


class Rule(XrayModel):
    tag: str
    outbound_tag: str
    protocol: list[RuleProtocolType] | None = Field(default=None)
    port: str | None = Field(default=None)
    domain: list[str] | None = Field(default=None)
    ip: list[str] | None = Field(default=None)


class Routing(XrayModel):
    domain_strategy: RoutingDomainStrategyType | None = Field(default=None)
    rules: list[Rule] = Field(default_factory=list)
