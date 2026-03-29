from contextlib import suppress
from typing import Iterator

from typer import Context

from app.controller.common import load_config, ClientData, RuleData
from app.defaults import XRAY_CONFIG_PATH
from app.model.xray import Outbound


def complete_client_name(_ctx: Context, _args: list[str], incomplete: str) -> Iterator[str]:
    with suppress(BaseException):
        config = load_config(XRAY_CONFIG_PATH)
        vless_inbound = config.get_vless_inbound()
        clients = vless_inbound.settings.clients if vless_inbound else []
        clients_names = (ClientData.from_model(client, i).name
                         for i, client in enumerate(clients or []))
        for name in clients_names:
            if name.startswith(incomplete):
                yield name


def complete_route_name(_ctx: Context, _args: list[str], incomplete: str) -> Iterator[str]:
    with suppress(BaseException):
        config = load_config(XRAY_CONFIG_PATH)
        rules = config.routing.rules if config.routing and config.routing.rules else []
        rules_names = (RuleData.from_model(rule, i).name for i, rule in enumerate(rules))
        for name in rules_names:
            if name.startswith(incomplete):
                yield name


def complete_outbound_name(_ctx: Context, _args: list[str], incomplete: str) -> Iterator[str]:
    with suppress(BaseException):
        for outbound in _get_outbounds(incomplete):
            if isinstance(outbound, dict):
                tag = outbound.get('tag')
                if not tag:
                    continue
                yield str(tag)
            else:
                tag: str | None = outbound.tag
                if not tag:
                    continue
                yield tag

def complete_vless_outbound_name(_ctx: Context, _args: list[str], incomplete: str) -> Iterator[str]:
    with suppress(BaseException):
        for outbound in _get_outbounds(incomplete):
            if isinstance(outbound, dict):
                tag = outbound.get('tag')
                protocol = outbound.get('protocol')
            else:
                tag = outbound.tag
                protocol = outbound.protocol
            if protocol == 'vless' and tag:
                yield str(tag)


def _get_outbounds(incomplete: str) -> Iterator[Outbound | dict]:
    config = load_config(XRAY_CONFIG_PATH)
    outbounds = config.outbounds or []
    for outbound in outbounds:
        if isinstance(outbound, dict):
            tag = outbound.get('tag', '')
        else:
            tag = outbound.tag or ''
        if tag.startswith(incomplete):
            yield outbound
