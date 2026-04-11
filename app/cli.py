from typing import Annotated

import typer
from typer import Typer, Option

from app.utils import detect_veepeenet_versions


def _version_callback(value: bool) -> None:
    if value:
        versions = detect_veepeenet_versions()
        typer.echo(
            f'VeePeeNET {versions.veepeenet_version} '
            f'build {versions.veepeenet_build} '
            f'(Xray {versions.xray_version})')
        raise typer.Exit()


app = Typer()


@app.callback()
def show_version(
        _version: Annotated[
            bool, Option('--version', help='Show version and exit.',
                         callback=_version_callback, is_eager=True)] = False,
) -> None:
    pass


clients = Typer()
routing = Typer()
outbounds = Typer()

app.add_typer(clients, name='clients', help='Manage clients')
app.add_typer(routing, name='routing', help='Manage routing')
app.add_typer(outbounds, name='outbounds', help='Manage outbounds')
