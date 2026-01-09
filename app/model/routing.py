from typing import Literal

from pydantic import Field, model_validator

from app.model.base import XrayModel


class Rule(XrayModel):
    tag: str
    outbound_tag: str
    protocol: list[str] | None = Field(default=None)
    port: str = Field(default=None)
    domain: list[str] | None = Field(default=None)
    ip: list[str] | None = Field(default=None)
    inbound_tag: list[str] | None = Field(default=None)

    @model_validator(mode='after')
    def check(self):
        if not any([self.protocol, self.port, self.domain, self.ip, self.inbound_tag]):
            raise ValueError(f'No conditions found for rule "{self.tag}"')
        if not self.outbound_tag:
            raise ValueError(f'No outbound tag found for rule "{self.tag}"')
        return self


class Routing(XrayModel):
    domain_strategy: Literal['AsIs', 'IPIfNonMatch', 'IPOnDemand'] = 'AsIs'
    rules: list[Rule] = Field(default_factory=list)
