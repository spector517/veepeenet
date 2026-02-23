from typer import Typer

app = Typer(add_completion=False)

clients = Typer(add_completion=False)
routing = Typer(add_completion=False)
outbounds = Typer(add_completion=False)

app.add_typer(clients, name='clients', help='Manage clients')
app.add_typer(routing, name='routing', help='Manage routing')
app.add_typer(outbounds, name='outbounds', help='Manage outbounds')
