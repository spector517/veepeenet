from typer import Typer

app = Typer(add_completion=False)

routing = Typer(add_completion=False)

app.add_typer(routing, name='routing', help='Manage routing')
