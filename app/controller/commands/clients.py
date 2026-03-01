from pathlib import Path
from typing import Annotated

from typer import Argument, Option, echo

from app.app import clients
from app.controller.common import (
    error_handler,
    load_config,
    exit_if_xray_config_not_found,
    check_and_install,
    ClientData,
)
from app.defaults import XRAY_CONFIG_PATH
from app.utils import (
    get_new_items,
    get_vless_client_url,
    remove_duplicates,
    get_existing_items,
    get_short_id,
    write_text_file
)
from app.view import ClientsView, ClientView


@clients.command(help='Register clients to service')
@error_handler(default_message='Error adding clients to service', default_code=20)
def add(client_names: Annotated[list[str],
        Argument(help='List of new client of server')],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    exit_if_xray_config_not_found()
    check_and_install()
    _add_clients(client_names)


@clients.command(help='Remove clients from service')
@error_handler(default_message='Error removing clients from service', default_code=20)
def remove(client_names: Annotated[list[str],
        Argument(help='List of clients to remove from Xray VLESS Reality server')],
           _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    exit_if_xray_config_not_found()
    check_and_install()
    _remove_clients(client_names)


@clients.command(help='List clients of service', name='list')
@error_handler(default_message='Error listing clients of service', default_code=20)
def show(
        json: Annotated[bool, Option(help='Show JSON formatted info')] = False,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    exit_if_xray_config_not_found()
    check_and_install()

    xray_config = load_config(XRAY_CONFIG_PATH)
    settings = xray_config.inbounds[0].settings
    host = xray_config.inbounds[0].listen

    clients_data = [ClientData.from_model(client, host) for client in settings.clients]
    clients_views = [ClientView(
        name=client_data.name,
        url=get_vless_client_url(client_data.name, xray_config))
                     for client_data in clients_data]
    view = ClientsView(clients=clients_views)

    if json:
        echo(view.model_dump_json(exclude_none=True, indent=2))
    else:
        echo(repr(view))


def _add_clients(names: list[str], xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    xray_config = load_config(xray_config_path)
    settings = xray_config.inbounds[0].settings
    host = xray_config.inbounds[0].listen
    reality_settings = xray_config.inbounds[0].stream_settings.reality_settings

    existing_clients_data = [ClientData.from_model(client, host) for client in settings.clients]
    existing_names = [client_data.name for client_data in existing_clients_data]
    new_names = get_new_items(existing_names, remove_duplicates(names))
    already_existing_names = get_existing_items(existing_names, names)

    if already_existing_names:
        echo('These clients already exist and will be skipped: '
                   + ', '.join(already_existing_names))
    if not new_names:
        echo('No new clients found')
        return

    existing_short_ids = [client_data.short_id for client_data in existing_clients_data]
    for name in new_names:
        short_id = get_short_id(existing_short_ids)
        existing_short_ids.append(short_id)
        new_client_data = ClientData(name=name, short_id=short_id, host=host)
        existing_clients_data.append(new_client_data)

    settings.clients = [client_data.to_model() for client_data in existing_clients_data]
    reality_settings.short_ids = [f'{short_id:04}' for short_id in existing_short_ids]

    write_text_file(
        xray_config_path,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    echo('Added new clients: ' + ', '.join(new_names))


def _remove_clients(names: list[str], xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    xray_config = load_config(xray_config_path)
    existing_clients = xray_config.inbounds[0].settings.clients
    host = xray_config.inbounds[0].listen
    reality_settings = xray_config.inbounds[0].stream_settings.reality_settings
    settings = xray_config.inbounds[0].settings

    existing_clients_data = [ClientData.from_model(client, host) for client in existing_clients]
    existing_names = [client_data.name for client_data in existing_clients_data]
    removable_names = get_existing_items(existing_names, remove_duplicates(names))
    unknown_names = get_new_items(existing_names, names)

    if unknown_names:
        echo('These clients are unknown and will be skipped: '
                   + ', '.join(unknown_names))
    if not removable_names:
        echo('No clients found to remove')
        return

    remaining_clients_data = [cd for cd in existing_clients_data if cd.name not in removable_names]
    remaining_short_ids = [cd.short_id for cd in remaining_clients_data]

    settings.clients = [client_data.to_model() for client_data in remaining_clients_data]
    reality_settings.short_ids = [f'{short_id:04}' for short_id in remaining_short_ids]

    write_text_file(
        xray_config_path,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    echo('Removed clients: ' + ', '.join(removable_names))
