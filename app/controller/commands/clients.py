from pathlib import Path
from typing import Annotated
from typer import Argument, Option

from app.app import app
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
    remove_duplicates,
    get_existing_items,
    get_short_id,
    write_text_file
)


@app.command(help='Register clients to service')
@error_handler(default_message='Error adding clients to service')
def add_clients(client_names: Annotated[list[str],
        Argument(help='List of new client of server')],
                _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    exit_if_xray_config_not_found()
    check_and_install()
    __add_clients(client_names)


@app.command(help='Remove clients from service')
@error_handler(default_message='Error removing clients from service')
def remove_clients(client_names: Annotated[list[str],
        Argument(help='List of clients to remove from Xray VLESS Reality server')],
                   _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    exit_if_xray_config_not_found()
    check_and_install()
    __remove_clients(client_names)



def __add_clients(names: list[str], xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    xray_config = load_config(xray_config_path)
    settings = xray_config.inbounds[0].settings
    host = xray_config.inbounds[0].listen
    reality_settings = xray_config.inbounds[0].stream_settings.reality_settings

    existing_clients_data = [ClientData.from_model(client, host) for client in settings.clients]
    existing_names = [client_data.name for client_data in existing_clients_data]
    new_names = get_new_items(existing_names, remove_duplicates(names))
    already_existing_names = get_existing_items(existing_names, names)

    if already_existing_names:
        print('These clients already exist and will be skipped:',
              ', '.join(already_existing_names))
    if not new_names:
        print('No new clients found')
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
    print('Added new clients:', ', '.join(new_names))


def __remove_clients(names: list[str], xray_config_path: Path = XRAY_CONFIG_PATH) -> None:
    xray_config = load_config(xray_config_path)
    clients = xray_config.inbounds[0].settings.clients
    host = xray_config.inbounds[0].listen
    reality_settings = xray_config.inbounds[0].stream_settings.reality_settings
    settings = xray_config.inbounds[0].settings

    existing_clients_data = [ClientData.from_model(client, host) for client in clients]
    existing_names = [client_data.name for client_data in existing_clients_data]
    removable_names = get_existing_items(existing_names, remove_duplicates(names))
    unknown_names = get_new_items(existing_names, names)

    if unknown_names:
        print('These clients are unknown and will be skipped:',
              ', '.join(unknown_names))
    if not removable_names:
        print('No clients found to remove')
        return

    existing_short_ids = [client_data.short_id for client_data in existing_clients_data]
    for existing_client_data in existing_clients_data:
        if existing_client_data.name in removable_names:
            existing_clients_data.remove(existing_client_data)
            existing_short_ids.remove(existing_client_data.short_id)

    settings.clients = [client_data.to_model() for client_data in existing_clients_data]
    reality_settings.short_ids = [f'{short_id:04}' for short_id in existing_short_ids]

    write_text_file(
        xray_config_path,
        xray_config.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        0o644)
    print('Removed clients:', ', '.join(removable_names))
