from functools import wraps
from typing import Annotated, Callable, Any

from typer import Typer, Option, Argument

from app import controller
from app.defaults import (
    VLESS_LISTEN_PORT,
    REALITY_HOST,
    REALITY_PORT,
)

app = Typer()


def handle_error(func: Callable[..., ...]) -> Callable[..., ...]:
    def get_error_text() -> str:
        errors = {
            config: 'Error during configuration Xray service',
            status: 'Error retrieving status of Xray service',
            start: 'Error starting Xray service',
            stop: 'Error stopping Xray service',
            restart: 'Error restarting Xray service',
            add_clients: 'Error adding clients to Xray service',
            remove_clients: 'Error removing clients from Xray service',
        }
        try:
            return errors[func]
        except KeyError:
            return 'Unknown error'

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any | None:
        try:
            return func(*args, **kwargs)
        except Exception as e:  # pylint: disable=broad-exception-caught
            if '_debug' in kwargs and kwargs['_debug']:
                raise
            print(f'{get_error_text()}: {e}')
            return None

    return wrapper


@app.command(help='Initialize Xray VLESS server with Reality')
@handle_error
def config(
        host: Annotated[str, Option(
            help=('Public interface of server.'
                  ' Using `hostname -i` if not specified.'
                  ' It is recommended to specify manually.'))] = None,
        port: Annotated[int, Option(help='Inbound port.')] = VLESS_LISTEN_PORT,
        reality_host: Annotated[str, Option(help='Reality host.')] = REALITY_HOST,
        reality_port: Annotated[int, Option(help='Reality port.')] = REALITY_PORT,
        clean: Annotated[bool, Option(help='Override current configuration')] = False,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False
) -> None:
    controller.check_and_install()
    controller.config(host, port, reality_host, reality_port, clean)


@app.command(help='Show Xray service status')
@handle_error
def status(json: Annotated[bool, Option(help='Show in JSON-format')] = False,
           _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    controller.exit_if_xray_config_not_found()
    controller.check_and_install()
    server_view = controller.status()
    if json:
        print(server_view.model_dump_json(exclude_none=True, indent=2))
    else:
        print(repr(server_view))


@app.command(help='Start Xray service')
@handle_error
def start(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    controller.exit_if_xray_config_not_found()
    controller.check_and_install()
    controller.start()


@app.command(help='Stop Xray service')
@handle_error
def stop(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    controller.exit_if_xray_config_not_found()
    controller.check_and_install()
    controller.stop()


@app.command(help='Restart Xray service')
@handle_error
def restart(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    controller.exit_if_xray_config_not_found()
    controller.check_and_install()
    controller.stop()
    controller.start()


@app.command(help='Add clients to Xray VLESS Reality server')
@handle_error
def add_clients(client_names: Annotated[list[str],
        Argument(help='List of new client of Xray VLESS Reality server')],
                    _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    controller.exit_if_xray_config_not_found()
    controller.check_and_install()
    controller.add_clients(client_names)


@app.command(help='Remove clients from Xray VLESS Reality server')
@handle_error
def remove_clients(client_names: Annotated[list[str],
        Argument(help='List of clients to remove from Xray VLESS Reality server')],
                    _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    controller.exit_if_xray_config_not_found()
    controller.check_and_install()
    controller.remove_clients(client_names)


if __name__ == "__main__":
    app()
