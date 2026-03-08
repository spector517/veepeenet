from typing import Literal

from pydantic import BaseModel, Field


class ClientView(BaseModel):
    name: str
    url: str

    def __repr__(self) -> str:
        return f'{self.name}: {self.url}'


class ClientsView(BaseModel):
    clients: list[ClientView]

    def __repr__(self) -> str:
        padding = ' ' * 2

        clients_str = '==================== Xray clients  ====================\n'

        if not self.clients:
            clients_str += f'{padding}Server has no clients\n'
            return clients_str

        client_block_breaker = '-------------------------------------------------------\n'
        for client in self.clients:
            clients_str += client_block_breaker
            client_repr = '\n'.join(
                [f'{padding * 2}{line}' for line in repr(client).splitlines()])
            clients_str += f'{client_repr}\n'
            clients_str += client_block_breaker
        clients_str += '======================================================='
        return clients_str


class ServerView(BaseModel):
    veepeenet_version: str
    veepeenet_build: int
    xray_version: str
    server_status: Literal['running', 'stopped']
    enabled: bool
    uptime: str | None = Field(default=None)
    server_host: str
    server_port: int
    reality_address: str
    reality_names: list[str]
    clients: list[str]
    outbounds: list[str]

    def __repr__(self) -> str:
        padding = ' ' * 2

        clients_str = ', '.join(self.clients) \
            if self.clients else 'Server has no clients'
        return ('=========== '
        f'VeePeeNET {self.veepeenet_version} build {self.veepeenet_build}'
        ' ===========\n'
        'Xray server info:\n'
        f'{padding}version: {self.xray_version}\n'
        f"{padding}status: {self.server_status} ({'enabled' if self.enabled else 'disabled' })\n"
        f"{padding}uptime: {self.uptime or 'unknown'}\n"
        f'{padding}address: {self.server_host}:{self.server_port}\n'
        f'{padding}reality_address: {self.reality_address}\n'
        f'{padding}reality_names: {", ".join(self.reality_names)}\n'
        f'{padding}clients: {clients_str}\n'
        f'{padding}outbounds: {", ".join(self.outbounds)}\n'
        '=======================================================')


class RuleView(BaseModel):
    name: str
    domains: list[str] | None = Field(default=None)
    ips: list[str] | None = Field(default=None)
    ports: str | None = Field(default=None)
    protocols: list[str] | None = Field(default=None)
    outbound_name: str
    priority: int

    def __repr__(self) -> str:
        padding = ' ' * 2
        rule_str = f'#{self.priority} {self.name}: --> {self.outbound_name}\n'

        if self.domains:
            rule_str += f'{padding}Domains: {", ".join(self.domains)}\n'
        if self.ips:
            rule_str += f'{padding}IPs: {", ".join(self.ips)}\n'
        if self.ports:
            rule_str += f'{padding}Ports: {self.ports}\n'
        if self.protocols:
            rule_str += f'{padding}Protocols: {", ".join(self.protocols)}\n'

        return rule_str

class RoutingView(BaseModel):
    domain_strategy: str | None = Field(default=None)
    rules: list[RuleView] | None = Field(default=None)

    def __repr__(self) -> str:
        padding = ' ' * 2

        routing_str = '==================== Xray routing  ====================\n'

        if not self.domain_strategy and not self.rules:
            routing_str += f'{padding}No routing rules configured\n'
            return routing_str

        routing_str += f'{padding}Domain strategy: {self.domain_strategy}\n'
        if not self.rules:
            return routing_str
        rule_block_breaker = '-------------------------------------------------------\n'
        for rule in self.rules:
            routing_str += rule_block_breaker
            rule_repr = '\n'.join(
                [f'{padding * 2}{line}' for line in repr(rule).splitlines()])
            routing_str += f'{rule_repr}\n'
            routing_str += rule_block_breaker
        routing_str += '======================================================='
        return routing_str


class VersionsView(BaseModel):
    veepeenet_version: str
    veepeenet_build: int
    xray_version: str


class XrayReleasesView(BaseModel):
    releases: list[str]

    def __repr__(self) -> str:
        padding = ' ' * 2
        result = '================ Available Xray releases ===============\n'
        for i, version in enumerate(self.releases, start=1):
            result += f'{padding}{i}. {version}\n'
        result += '======================================================='
        return result
