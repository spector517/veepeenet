from typing import Literal

from pydantic import BaseModel, Field
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from app.defaults import (
    STYLE_WARN,
    STYLE_VALUE,
    STYLE_URL,
    STYLE_ACCENT_UP,
    STYLE_ACCENT_DOWN,
    STYLE_ACCENT_NEUTRAL,
    STYLE_OK,
    STYLE_DIM,
    STYLE_REGULAR
)


def joined_bold(items: list[str], fallback: str | None = None) -> Text:
    if not items:
        return Text(fallback or '', STYLE_ACCENT_NEUTRAL)
    return Text(', ', no_wrap=True).join(Text(item, STYLE_VALUE) for item in items)

def row(label: Text, value: Text) -> Text:
    return Text.assemble(label, value)

class ClientView(BaseModel):
    name: str
    url: str

    def rich_repr(self) -> Group:
        return Group(
            Text(self.name, STYLE_VALUE),
            Text(self.url, STYLE_URL, no_wrap=True)
        )


class ClientsView(BaseModel):
    clients: list[ClientView]

    def rich_repr(self) -> Group:
        if not self.clients:
            return Group(Text('Server has no clients', STYLE_WARN))

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
                (self.name, STYLE_VALUE),
                ('(', ''),
                (self.address, STYLE_URL),
                (')', ''))
        return Text(self.name, STYLE_VALUE)


class ServerView(BaseModel):
    veepeenet_version: str
    veepeenet_build: int
    xray_version: str
    server_status: Literal['running', 'stopped']
    enabled: bool
    uptime: str | None = Field(default=None)
    restart_required: bool
    server_host: str
    server_port: int
    reality_address: str
    reality_names: list[str]
    clients: list[str]
    outbounds: list[OutboundView]

    def rich_repr(self) -> Panel:
        run_status = Text(
            self.server_status,
            STYLE_ACCENT_UP if self.server_status == 'running' else STYLE_ACCENT_DOWN,
        )
        enabled_status = Text(
            'enabled' if self.enabled else 'disabled',
            STYLE_ACCENT_UP if self.enabled else STYLE_ACCENT_NEUTRAL,
        )

        outbounds_text = (
            Text(', ').join(ob.rich_text() for ob in self.outbounds)
            if self.outbounds
            else Text('No outbounds', STYLE_ACCENT_NEUTRAL)
        )

        content = Text('\n').join([
            row(Text('status: ', STYLE_REGULAR),
                Text.assemble(run_status, ' (', enabled_status, ')')),
            row(Text('uptime: ', STYLE_REGULAR), Text(
                self.uptime, STYLE_ACCENT_UP) if self.uptime else Text(
                'n/a', STYLE_ACCENT_DOWN)),
            row(Text('xray_version: ', STYLE_REGULAR),
                Text(self.xray_version, STYLE_VALUE)),
            row(Text('address: ', STYLE_REGULAR),
                Text(f'{self.server_host}:{self.server_port}', STYLE_VALUE)),
            row(Text('reality_address: ', STYLE_REGULAR),
                Text(self.reality_address, STYLE_VALUE)),
            row(Text('reality_names: ', STYLE_REGULAR), joined_bold(self.reality_names)),
            row(Text('clients: ', STYLE_REGULAR),
                joined_bold(self.clients, 'Server has no clients')),
            row(Text('outbounds: ', STYLE_REGULAR), outbounds_text),
        ])

        border_style: str
        if self.server_status == 'running':
            border_style = STYLE_WARN if self.restart_required else STYLE_OK
        else:
            border_style = STYLE_DIM

        title = Text('Xray server information')
        if self.restart_required:
            title.append(Text(' (configuration changes detected, restart required)'))

        return Panel(
            content,
            title=title,
            subtitle=f'VeePeeNET {self.veepeenet_version}',
            title_align='left',
            subtitle_align='right',
            border_style=border_style,
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
            row(Text('name: ', STYLE_REGULAR), Text(self.name, STYLE_VALUE)),
        ]

        if self.domains:
            content_lines.append(
                row(Text('domains: ', STYLE_REGULAR),joined_bold(self.domains)))
        if self.ips:
            content_lines.append(
                row(Text('ips: ', STYLE_REGULAR), joined_bold(self.ips)))
        if self.ports:
            content_lines.append(
                row(Text('ports: ', STYLE_REGULAR), Text(self.ports, STYLE_VALUE)))
        if self.protocols:
            content_lines.append(
                row(Text('protocols: ', STYLE_REGULAR), joined_bold(self.protocols)))

        content = Text('\n').join(content_lines)
        title = Text.assemble(
            (f'Rule #{self.priority} ', STYLE_REGULAR),
            (self.name, STYLE_ACCENT_UP),
            (' --> ', STYLE_ACCENT_NEUTRAL),
            (self.outbound_name, STYLE_ACCENT_UP)
        )
        return Panel(
            content,
            title=title,
            title_align='left',
        )


class RoutingView(BaseModel):
    domain_strategy: str | None = Field(default=None)
    rules: list[RuleView] | None = Field(default=None)

    def rich_repr(self) -> Group:
        if not self.domain_strategy and not self.rules:
            return Group(Text('No routing rules configured', STYLE_WARN))

        content_parts: list[Group | Text | Panel] = [
            Panel(Text.assemble(
                ('Domain strategy: ', STYLE_REGULAR),
                (self.domain_strategy, STYLE_VALUE)
            ))
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
                Text(f'{i}. ', STYLE_REGULAR).append(Text(version, STYLE_VALUE)))
        return Panel(
            Text('\n').join(rich_releases),
            title=Text('Available Xray versions', STYLE_REGULAR),
            title_align='left',
            border_style=STYLE_DIM,
        )
