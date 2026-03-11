from contextlib import suppress
from typing import Iterator

from typer import Context

from app.controller.common import load_config, ClientData, RuleData
from app.defaults import XRAY_CONFIG_PATH
from app.model.xray import Outbound


def complete_client_name(_ctx: Context, _args: list[str], incomplete: str) -> Iterator[str]:
    with suppress(BaseException):
        config = load_config(XRAY_CONFIG_PATH)
        clients_names = (ClientData.from_model(client, config.veepeenet.host).name
                         for client in config.get_vless_inbound().settings.clients)
        for name in clients_names:
            if name.startswith(incomplete):
                yield name


def complete_route_name(_ctx: Context, _args: list[str], incomplete: str) -> Iterator[str]:
    with suppress(BaseException):
        config = load_config(XRAY_CONFIG_PATH)
        rules_names = (RuleData.from_model(rule, i).name
                       for i, rule in enumerate(config.routing.rules))
        for name in rules_names:
            if name.startswith(incomplete):
                yield name


def complete_outbound_name(_ctx: Context, _args: list[str], incomplete: str) -> Iterator[str]:
    with suppress(BaseException):
        for outbound in _get_outbounds(incomplete):
            yield outbound.get('tag') if isinstance(outbound, dict) else outbound.tag


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
                yield tag


def _get_outbounds(incomplete: str) -> Iterator[Outbound | dict]:
    config = load_config(XRAY_CONFIG_PATH)
    for outbound in config.outbounds:
        if isinstance(outbound, dict):
            tag = outbound.get('tag', '')
        else:
            tag = outbound.tag or ''
        if tag.startswith(incomplete):
            yield outbound
