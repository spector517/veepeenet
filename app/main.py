from functools import wraps
from typing import Annotated, Callable, Any

from typer import Typer, Option, Argument

from app.controller import configure, state, clients, outbound, common
from app.defaults import (
    VLESS_LISTEN_PORT,
    VLESS_OUTBOUND_PORT,
    VLESS_OUTBOUND_SPIDER_X,
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
            add_outbound: 'Error adding outbound clients to Xray service',
            change_outbound: 'Error changing VLESS outbound connection',
            remove_outbound: 'Error removing VLESS outbound connection',
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
        reality_names: Annotated[
            list[str],
            Option(help='Available Reality server names.',
                   show_default='Reality host')] = None,
        clean: Annotated[bool, Option(help='Override current configuration')] = False,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False
) -> None:
    common.check_and_install()
    configure.config(
        host, port, reality_host, reality_port, reality_names or [REALITY_HOST], clean)


@app.command(help='Show Xray service status')
@handle_error
def status(json: Annotated[bool, Option(help='Show in JSON-format')] = False,
           _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    common.exit_if_xray_config_not_found()
    common.check_and_install()
    server_view = state.status()
    if json:
        print(server_view.model_dump_json(exclude_none=True, indent=2))
    else:
        print(repr(server_view))


@app.command(help='Start Xray service')
@handle_error
def start(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    common.exit_if_xray_config_not_found()
    common.check_and_install()
    state.start()


@app.command(help='Stop Xray service')
@handle_error
def stop(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    common.exit_if_xray_config_not_found()
    common.check_and_install()
    state.stop()


@app.command(help='Restart Xray service')
@handle_error
def restart(_debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    common.exit_if_xray_config_not_found()
    common.check_and_install()
    state.restart()


@app.command(help='Add clients to Xray VLESS Reality server')
@handle_error
def add_clients(client_names: Annotated[list[str],
        Argument(help='List of new client of Xray VLESS Reality server')],
                    _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    common.exit_if_xray_config_not_found()
    common.check_and_install()
    clients.add_clients(client_names)


@app.command(help='Remove clients from Xray VLESS Reality server')
@handle_error
def remove_clients(client_names: Annotated[list[str],
        Argument(help='List of clients to remove from Xray VLESS Reality server')],
                    _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    common.exit_if_xray_config_not_found()
    common.check_and_install()
    clients.remove_clients(client_names)


@app.command(help='Add new VLESS outbound VLESS Reality connection')
@handle_error
def add_outbound(
        name: Annotated[str, Argument(help='Outbound name')],
        address: Annotated[str, Option(help='Outbound address (ip or domain name)')],
        uuid: Annotated[str, Option(help='VLESS client identifier')],
        sni: Annotated[str, Option(help='Server name of target server')],
        password: Annotated[str, Option(help='Public key of target server')],
        short_id: Annotated[str, Option(help='One of short_id of target server')],
        spider_x: Annotated[
            str,
            Option(help='Initial path and parameters for the spider')] = VLESS_OUTBOUND_SPIDER_X,
        port: Annotated[
            int | None,
            Option(help='VLESS outbound port')] = VLESS_OUTBOUND_PORT,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    common.exit_if_xray_config_not_found()
    common.check_and_install()
    outbound.add_vless_outbound(name, address, port, uuid, sni, password, short_id, spider_x)


@app.command(help='Remove VLESS outbound connection')
@handle_error
def remove_outbound(
        name: Annotated[str, Argument(help='Outbound name')],
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    common.exit_if_xray_config_not_found()
    common.check_and_install()
    outbound.remove_vless_outbound(name)


@app.command(help='Change VLESS outbound connection parameters')
@handle_error
def change_outbound(
        name: Annotated[str, Argument(help='Outbound name')],
        address: Annotated[str | None, Option(help='Outbound address (ip or domain name)')] = None,
        uuid: Annotated[str | None, Option(help='VLESS client identifier')] = None,
        sni: Annotated[str | None, Option(help='Server name of target server')] = None,
        password: Annotated[str | None, Option(help='Public key of target server')] = None,
        short_id: Annotated[str | None, Option(help='One of short_id of target server')] = None,
        spider_x: Annotated[
            str | None,
            Option(help='Initial path and parameters for the spider')] = None,
        port: Annotated[
            int | None,
            Option(help='VLESS outbound port')] = None,
        _debug: Annotated[bool, Option('--debug', hidden=True)] = False) -> None:
    common.exit_if_xray_config_not_found()
    common.check_and_install()
    outbound.change_vless_outbound(name, address, port, uuid, sni, password, short_id, spider_x)


if __name__ == "__main__":
    app()
