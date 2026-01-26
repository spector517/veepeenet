from pathlib import Path
from sys import getdefaultencoding
from typing import Annotated

from typer import run, Argument

from app.model.xray import Xray, FreedomOutbound, BlackholeOutbound
from app.defaults import XRAY_CONFIG_PATH
from app.utils import write_text_file


def migrate_xray_config(
        host: Annotated[str, Argument(
            help=(
                'External address of your Xray server.'
                ' Maybe ip or domain name'))],
        source_xray_config_path: Path = XRAY_CONFIG_PATH,
        dest_xray_config_path: Path = XRAY_CONFIG_PATH
) -> None:
    try:
        xray_config_content = source_xray_config_path.read_text(getdefaultencoding())
        xray = Xray.model_validate_json(xray_config_content)
        clients = xray.inbounds[0].settings.clients
        short_ids = xray.inbounds[0].stream_settings.reality_settings.short_ids

        xray.inbounds[0].listen = host

        if len(clients) != len(short_ids):
            raise ValueError("Number of clients does not match number of short IDs.")
        for client, short_id in zip(clients, short_ids):
            name = f'{client.email.split('@')[0]}.{short_id}'
            domain = client.email.split('@')[1]
            client.email = f'{name}@{domain}'

        xray.outbounds = [FreedomOutbound(), BlackholeOutbound()]

        write_text_file(
            dest_xray_config_path,
            xray.model_dump_json(by_alias=True, exclude_none=True, indent=2),
            0o644,
        )

    except Exception as e:
        print("Failed to migrate Xray config:", e)
        raise


def main():
    run(migrate_xray_config)


if __name__ == "__main__":
    main()
