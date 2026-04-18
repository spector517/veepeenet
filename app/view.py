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
from app.model.types import FingerprintType


def joined_bold(items: list[str], fallback: str | None = None) -> Text:
    if not items:
        return Text(fallback or '', STYLE_ACCENT_NEUTRAL)
    return Text(', ').join(Text(item, STYLE_VALUE) for item in items)

def row(label: Text, value: Text) -> Text:
    return Text.assemble(label, value)

class ClientView(BaseModel):
    name: str
    url: str

    def rich_repr_short(self) -> Text:
        return Text(self.name, STYLE_VALUE)

    def rich_repr(self) -> Group:
        return Group(
            Text(self.name, STYLE_VALUE),
            Text(self.url, STYLE_URL, no_wrap=True))


class ClientsView(BaseModel):
    clients: list[ClientView]

    def rich_repr_short(self) -> Text:
        if not self.clients:
            return Text('Server has no clients', STYLE_WARN)
        return Text(', ').join(client.rich_repr_short() for client in self.clients)

    def rich_repr(self) -> Group:
        if not self.clients:
            return Group(Text('Server has no clients', STYLE_WARN))

        client_panels: list[Group | str] = []
        for client in self.clients:
            client_panels += [client.rich_repr(), '']

        return Group(*client_panels)


class RuleView(BaseModel):
    name: str
    domains: list[str] | None = Field(default=None)
    ips: list[str] | None = Field(default=None)
    ports: str | None = Field(default=None)
    protocols: list[str] | None = Field(default=None)
    outbound_name: str
    priority: int

    def rich_repr_short(self) -> Text:
        return Text.assemble(
            (self.name, STYLE_VALUE),
            (' > ', STYLE_ACCENT_NEUTRAL),
            (self.outbound_name, STYLE_VALUE)
        )

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

    def rich_repr_short(self) -> Text:
        content = (rule.rich_repr_short() for rule in self.rules or [])
        if self.rules:
            return Text(', ').join(content)
        return Text('No routing rules configured', STYLE_WARN)

    def rich_repr(self) -> Group:
        if not self.domain_strategy and not self.rules:
            return Group(Text('No routing rules configured', STYLE_WARN))

        content_parts: list[Group | Text | Panel] = [
            Panel(Text.assemble(
                ('Domain strategy: ', STYLE_REGULAR),
                (self.domain_strategy or 'AsIs', STYLE_VALUE)
            ))
        ]

        if self.rules:
            # pylint: disable=not-an-iterable
            for rule in self.rules:
                content_parts.append(rule.rich_repr())

        return Group(*content_parts)


class OutboundView(BaseModel):
    name: str
    address: str | None = Field(default=None)
    uuid: str | None = Field(default=None)
    sni: str | None = Field(default=None)
    short_id: str | None = Field(default=None)
    password: str | None = Field(default=None)
    spider_x: str | None = Field(default=None)
    port: int | None = Field(default=None)
    fingerprint: FingerprintType | None = Field(default=None)
    interface: str | None = Field(default=None)

    def rich_text_short(self) -> Text:
        if self.address:
            return Text.assemble(
                (self.name, STYLE_VALUE),
                ('(', ''),
                (self.address + (f':{self.port}' if self.port else ''), STYLE_URL),
                (')', ''))
        return Text(self.name, STYLE_VALUE)

    def rich_text(self) -> Panel:
        content_lines: list[Text] = []

        if self.address:
            addr = self.address + (f':{self.port}' if self.port else '')
            content_lines.append(row(Text('address: ', STYLE_REGULAR), Text(addr, STYLE_VALUE)))
        if self.uuid:
            content_lines.append(row(Text('uuid: ', STYLE_REGULAR), Text(self.uuid, STYLE_VALUE)))
        if self.sni:
            content_lines.append(row(Text('sni: ', STYLE_REGULAR), Text(self.sni, STYLE_VALUE)))
        if self.short_id:
            content_lines.append(row(Text('short_id: ', STYLE_REGULAR), Text(self.short_id, STYLE_VALUE)))
        if self.password:
            content_lines.append(row(Text('password: ', STYLE_REGULAR), Text(self.password, STYLE_VALUE)))
        if self.spider_x:
            content_lines.append(row(Text('spider_x: ', STYLE_REGULAR), Text(self.spider_x, STYLE_VALUE)))
        if self.fingerprint:
            content_lines.append(
                row(Text('fingerprint: ', STYLE_REGULAR), Text(self.fingerprint, STYLE_VALUE)))
        if self.interface:
            content_lines.append(row(Text('interface: ', STYLE_REGULAR), Text(self.interface, STYLE_VALUE)))

        content = Text('\n').join(content_lines) if content_lines else Text('No details', STYLE_DIM)
        return Panel(
            content,
            title=Text(self.name, STYLE_ACCENT_UP),
            title_align='left',
        )


class OutboundsView(BaseModel):
    outbounds: list[OutboundView]

    def rich_repr(self) -> Group:
        if not self.outbounds:
            return Group(Text('No Vless outbounds configured', STYLE_WARN))
        return Group(*[ob.rich_text() for ob in self.outbounds])


class ServerView(BaseModel):
    veepeenet_version: str
    veepeenet_build: int
    xray_version: str
    server_status: Literal['running', 'stopped']
    enabled: bool
    uptime: str | None = Field(default=None)
    restart_required: bool
    server_host: str
    server_port: str
    reality_address: str
    reality_names: list[str]
    clients: ClientsView
    routing: RoutingView
    outbounds: list[OutboundView]
    server_name: str | None = Field(default=None)

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
            Text(', ').join(ob.rich_text_short() for ob in self.outbounds)
            if self.outbounds
            else Text('No outbounds', STYLE_ACCENT_NEUTRAL)
        )

        content = Text('\n').join([
            row(Text('status: ', STYLE_REGULAR), Text.assemble(run_status, ' (', enabled_status, ')')),
            row(Text('uptime: ', STYLE_REGULAR), Text(
                self.uptime, STYLE_ACCENT_UP) if self.uptime else Text('n/a', STYLE_ACCENT_DOWN)),
            row(Text('xray_version: ', STYLE_REGULAR),Text(self.xray_version, STYLE_VALUE)),
            row(Text('address: ', STYLE_REGULAR),
                Text(f'{self.server_host}:{self.server_port}', STYLE_VALUE)),
            row(Text('reality_address: ', STYLE_REGULAR), Text(self.reality_address, STYLE_VALUE)),
            row(Text('reality_names: ', STYLE_REGULAR), joined_bold(self.reality_names)),
            row(Text('clients: ', STYLE_REGULAR), self.clients.rich_repr_short()),
            row(Text('rules: ', STYLE_REGULAR), self.routing.rich_repr_short()),
            row(Text('outbounds: ', STYLE_REGULAR), outbounds_text),
        ])

        border_style: str
        if self.server_status == 'running':
            border_style = STYLE_WARN if self.restart_required else STYLE_OK
        else:
            border_style = STYLE_DIM

        title = Text('Xray server information')
        if self.server_name:
            title = Text.assemble(
                ('[', STYLE_DIM),
                (self.server_name, STYLE_VALUE),
                ('] ', STYLE_DIM),
                title
            )
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
