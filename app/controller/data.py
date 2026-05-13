from typing import Self
from enum import StrEnum
from dataclasses import dataclass
from uuid import UUID, uuid4, uuid5

from xxhash import xxh64

from app.defaults import VLESS_LISTEN_INTERFACE
from app.model.routing import Rule
from app.model.vless_inbound import Client
from app.model.types import RuleProtocolType
from app.model.api import Stats
from app.model.veepeenet import VeePeeNetStats, TrafficStats


@dataclass
class ClientData:
    name: str
    short_id: str
    uuid: UUID

    def __init__(
            self, name: str,
            short_id: str | None = None,
            namespace: UUID | None = None,
            uuid: UUID | None = None) -> None:
        self.name = name
        self.short_id = short_id or xxh64(name).hexdigest()
        if uuid:
            self.uuid = uuid
        elif namespace:
            self.uuid = uuid5(namespace, name)
        else:
            self.uuid = uuid4()


    @staticmethod
    def get_name_by_email(email: str) -> str:
        return '.'.join(email.split('@')[0].split('.')[:-1])


    @classmethod
    def from_model(cls, client: Client, index: int) -> "ClientData":
        if client.email:
            name = cls.get_name_by_email(client.email)
            short_id = client.email.split('@')[0].split('.')[-1]
        else:
            name = f'client_{index}'
            short_id = xxh64(name).hexdigest()
        uuid = UUID(client.id)
        return ClientData(name=name, short_id=short_id, uuid=uuid)

    def to_model(self) -> Client:
        return Client(
            id=str(self.uuid),
            email=f'{self.name}.{self.short_id}@{VLESS_LISTEN_INTERFACE}'
        )


@dataclass
class RuleData:
    name: str
    outbound_name: str
    protocols: list[RuleProtocolType] | None
    ports: str | None
    domains: list[str] | None
    ips: list[str] | None
    priority: int

    @classmethod
    def from_model(cls, rule: Rule, number: int = 0) -> "RuleData":
        try:
            split_name = rule.tag.split('.') if rule.tag else ''
            priority = int(split_name[-1])
            name = '.'.join(split_name[:-1])
        except ValueError:
            priority = (number + 1) * 10
            name = rule.tag or f'rule_{priority}'
        return RuleData(name=name, outbound_name=rule.outbound_tag, protocols=rule.protocol,
                        ports=rule.port, domains=rule.domain, ips=rule.ip, priority=priority)

    def to_model(self) -> Rule:
        return Rule(
            tag=f'{self.name}.{self.priority}',
            outbound_tag=self.outbound_name,
            protocol=self.protocols,
            port=self.ports,
            domain=self.domains,
            ip=self.ips)


@dataclass
class StatsData:

    class SubjectType(StrEnum):
        INBOUND = 'inbound'
        OUTBOUND = 'outbound'
        CLIENT = 'user'

        @classmethod
        def from_name(cls, name: str) -> Self | None:
            for item in iter(cls):
                if item.value == name:
                    return item
            return None

    class DirectionType(StrEnum):
        UPLINK = 'uplink'
        DOWNLINK = 'downlink'

        @classmethod
        def from_name(cls, name: str) -> Self | None:
            for item in iter(cls):
                if item.value == name:
                    return item
            return None

    subject: SubjectType
    name: str
    direction: DirectionType
    traffic: int = 0

    @classmethod
    def from_api(cls, stats: Stats) -> "StatsData | None":
        parts = stats.name.split('>>>')
        if len(parts) != 4 or parts[2] != 'traffic':
            return None

        subject = cls.SubjectType.from_name(parts[0])
        if not subject:
            return None
        direction = cls.DirectionType.from_name(parts[3])
        if not direction:
            return None

        name = parts[1]
        if subject == cls.SubjectType.CLIENT:
            name = ClientData.get_name_by_email(name)

        return StatsData(subject, name, direction, stats.value or 0)


    def to_model(self) -> VeePeeNetStats:
        inbound_traffic: dict[str, TrafficStats] = {}
        client_traffic: dict[str, TrafficStats] = {}
        outbound_traffic: dict[str, TrafficStats] = {}

        if self.subject == self.SubjectType.INBOUND:
            if self.direction == self.DirectionType.DOWNLINK:
                inbound_traffic[self.name] = TrafficStats(downlink=self.traffic)
            else:
                inbound_traffic[self.name] = TrafficStats(uplink=self.traffic)
        elif self.subject == self.SubjectType.CLIENT:
            if self.direction == self.DirectionType.DOWNLINK:
                client_traffic[self.name] = TrafficStats(downlink=self.traffic)
            else:
                client_traffic[self.name] = TrafficStats(uplink=self.traffic)
        elif self.subject == self.SubjectType.OUTBOUND:
            if self.direction == self.DirectionType.DOWNLINK:
                outbound_traffic[self.name] = TrafficStats(downlink=self.traffic)
            else:
                outbound_traffic[self.name] = TrafficStats(uplink=self.traffic)
        return VeePeeNetStats(client=client_traffic, inbound=inbound_traffic, outbound=outbound_traffic)
