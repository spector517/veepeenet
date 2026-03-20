from typing import Literal

from pydantic import BaseModel, Field
from rich.console import Group
from rich.panel import Panel
from rich.text import Text


def joined_bold(items: list[str], fallback: str | None = None) -> Text:
    if not items:
        return Text(fallback or '', style='bold yellow')
    return Text(', ', no_wrap=True).join(Text(item, style='bold cyan') for item in items)

def row(label: str, value: Text) -> Text:
    return Text.assemble(label, value)

class ClientView(BaseModel):
    name: str
    url: str

    def rich_repr(self) -> Group:
        return Group(
            Text(self.name, style='bold cyan'),
            Text(self.url, style='magenta', no_wrap=True)
        )


class ClientsView(BaseModel):
    clients: list[ClientView]

    def rich_repr(self) -> Group:
        if not self.clients:
            return Group(Text('Server has no clients', style='yellow'))

        client_panels: list[Group | str] = []
        for client in self.clients:
            client_panels += [client.rich_repr(), '']

        return Group(*client_panels)


class OutboundView(BaseModel):
    name: str
    address: str | None = Field(default=None)

    def rich_text(self) -> Text:
        if self.address:
            return Text.assemble(
                (self.name, 'bold cyan'),
                (' (', ''),
                (self.address, 'dim'),
                (')', ''))
        return Text(self.name, 'bold cyan')


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
    outbounds: list[OutboundView]

    def rich_repr(self) -> Panel:
        run_status = Text(
            self.server_status,
            style='bold green' if self.server_status == 'running' else 'bold red',
        )
        enabled_status = Text(
            'enabled' if self.enabled else 'disabled',
            style='bold green' if self.enabled else 'bold yellow',
        )

        outbounds_text = (
            Text(', ').join(ob.rich_text() for ob in self.outbounds)
            if self.outbounds
            else Text('No outbounds', style='bold yellow')
        )

        content = Text('\n').join([
            row('status: ', Text.assemble(run_status, ' (', enabled_status, ')')),
            row('uptime: ', Text(
                self.uptime, style='bold green') if self.uptime else Text(
                'n/a', style='bold red')),
            row('xray_version: ', Text(self.xray_version, style='bold cyan')),
            row('address: ', Text(f'{self.server_host}:{self.server_port}', style='bold cyan')),
            row('reality_address: ', Text(self.reality_address, style='bold cyan')),
            row('reality_names: ', joined_bold(self.reality_names)),
            row('clients: ', joined_bold(self.clients, 'Server has no clients')),
            row('outbounds: ', outbounds_text),
        ])

        return Panel(
            content,
            title='Xray server information',
            subtitle=f'VeePeeNET {self.veepeenet_version}',
            title_align='left',
            subtitle_align='right',
            border_style='green' if self.server_status == 'running' else 'yellow',
        )


class RuleView(BaseModel):
    name: str
    domains: list[str] | None = Field(default=None)
    ips: list[str] | None = Field(default=None)
    ports: str | None = Field(default=None)
    protocols: list[str] | None = Field(default=None)
    outbound_name: str
    priority: int

    def rich_repr(self) -> Panel:
        content_lines: list[Text] = [
            row('name: ', Text(self.name, style='bold cyan')),
        ]

        if self.domains:
            content_lines.append(row('domains: ', joined_bold(self.domains)))
        if self.ips:
            content_lines.append(row('ips: ', joined_bold(self.ips)))
        if self.ports:
            content_lines.append(row('ports: ', Text(self.ports, style='bold cyan')))
        if self.protocols:
            content_lines.append(row('protocols: ', joined_bold(self.protocols)))

        content = Text('\n').join(content_lines)
        title = Text.assemble(
            f'Rule #{self.priority} ',
            (self.name, 'bold green'),
            ' --> ',
            (self.outbound_name, 'bold green')
        )
        return Panel(
            content,
            title=title,
            title_align='left',
            border_style='magenta',
        )


class RoutingView(BaseModel):
    domain_strategy: str | None = Field(default=None)
    rules: list[RuleView] | None = Field(default=None)

    def rich_repr(self) -> Group:
        if not self.domain_strategy and not self.rules:
            return Group(Text('No routing rules configured', style='yellow'))

        content_parts: list[Group | Text | Panel | str] = [
            Text.assemble(
                ('Domain strategy: ', 'magenta'),
                    (self.domain_strategy, 'bold cyan')
            )
        ]

        if self.rules:
            # pylint: disable=not-an-iterable
            for rule in self.rules:
                content_parts.append(rule.rich_repr())

        return Group(*content_parts)


class VersionsView(BaseModel):
    veepeenet_version: str
    veepeenet_build: int
    xray_version: str


class XrayReleasesView(BaseModel):
    releases: list[str]

    def rich_repr(self) -> Panel:
        rich_releases: list[Text] = []
        for i, version in enumerate(self.releases, start=1):
            rich_releases.append(
                Text(f'{i}. ', style='bold green').append(Text(version, style='bold cyan')))
        return Panel(
            Text('\n').join(rich_releases),
            title=Text('Available Xray versions', style='bold'),
            title_align='left',
        )
