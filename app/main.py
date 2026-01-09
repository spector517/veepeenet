from typing import Annotated

from typer import Typer, Option, Argument

from app.defaults import (
    VLESS_LISTEN_PORT,
    REALITY_HOST,
    REALITY_PORT,
)
import app.controller as controller

app = Typer()


@app.command(help='Initialize Xray VLESS server with Reality')
def config(
        host: Annotated[str, Option(
            help=('Public interface of server.'
                  ' Using `hostname -i` if not specified.'
                  ' It is recommended to specify manually.'))] = None,
        port: Annotated[int, Option(help='Inbound port.')] = VLESS_LISTEN_PORT,
        reality_host: Annotated[str, Option(help='Reality host.')] = REALITY_HOST,
        reality_port: Annotated[int, Option(help='Reality port.')] = REALITY_PORT,
        clean: Annotated[bool, Option(help='Override current configuration')] = False,
        debug: Annotated[bool, Option(hidden=True)] = False
) -> None:
    try:
        controller.check_and_prepare()
        controller.config(host, port, reality_host, reality_port, clean)
        print('Configuration completed')
    except Exception as e:
        print(f'Error during initialization: {e}')
        if debug:
            raise e


@app.command(help='Show Xray service status')
def status(json: Annotated[bool, Option(help='Show in JSON-format')] = False,
           debug: Annotated[bool, Option(hidden=True)] = False
           ) -> None:
    try:
        controller.check_and_prepare()
        server_view = controller.status()
        if json:
            print(server_view.model_dump_json(exclude_none=True, indent=2))
        else:
            print(repr(server_view))
    except Exception as e:
        print(f'Error retrieving status: {e}')
        if debug:
            raise e


@app.command(help='Start Xray service')
def start(debug: Annotated[bool, Option(hidden=True)] = False) -> None:
    try:
        controller.check_and_prepare()
        controller.start()
    except Exception as e:
        print(f'Error starting Xray service: {e}')
        if debug:
            raise e


@app.command(help='Stop Xray service')
def stop(debug: Annotated[bool, Option(hidden=True)] = False) -> None:
    try:
        controller.check_and_prepare()
        controller.stop()
    except Exception as e:
        print(f'Error stopping Xray service: {e}')
        if debug:
            raise e


@app.command(help='Restart Xray service')
def restart(debug: Annotated[bool, Option(hidden=True)] = False) -> None:
    try:
        controller.check_and_prepare()
        controller.stop()
        controller.start()
    except Exception as e:
        print(f'Error restarting Xray service: {e}')
        if debug:
            raise e


@app.command(help='Add clients to Xray VLESS Reality server')
def add_clients(client_names: Annotated[list[str],
        Argument(help='List of new client of Xray VLESS Reality server')],
        debug: Annotated[bool, Option(hidden=True)] = False) -> None:
    try:
        controller.check_and_prepare()
        controller.add_clients(client_names)
    except Exception as e:
        print(f'Error adding clients: {e}')
        if debug:
            raise e


@app.command()
def remove_clients() -> None:
    ...


if __name__ == "__main__":
    app()
