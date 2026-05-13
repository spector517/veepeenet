from typing import Self
from pydantic import Field

from app.model.base import XrayModel


class TrafficStats(XrayModel):
    uplink: int = 0
    downlink: int = 0

    def __iadd__(self, other: "TrafficStats") -> Self:
        self.uplink += other.uplink
        self.downlink += other.downlink
        return self


class VeePeeNetStats(XrayModel):
    client: dict[str, TrafficStats] = Field(default_factory=dict)
    inbound: dict[str, TrafficStats] = Field(default_factory=dict)
    outbound: dict[str, TrafficStats] = Field(default_factory=dict)

    def __iadd__(self, other: "VeePeeNetStats") -> Self:
        for client, stats in other.client.items():
            if client not in self.client:
                self.client[client] = TrafficStats()
            self.client[client] += stats

        for inbound, stats in other.inbound.items():
            if inbound not in self.inbound:
                self.inbound[inbound] = TrafficStats()
            self.inbound[inbound] += stats

        for outbound, stats in other.outbound.items():
            if outbound not in self.outbound:
                self.outbound[outbound] = TrafficStats()
            self.outbound[outbound] += stats
        return self


class VeePeeNet(XrayModel):
    host: str
    namespace: str
    name: str | None = None
    stats: VeePeeNetStats = Field(default_factory=VeePeeNetStats)
