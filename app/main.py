# pylint: disable=unused-import

# noinspection PyUnusedImports
import app.controller.commands.clients
# noinspection PyUnusedImports
import app.controller.commands.configure
# noinspection PyUnusedImports
import app.controller.commands.outbound
# noinspection PyUnusedImports
import app.controller.commands.state
# noinspection PyUnusedImports
import app.controller.commands.routing

from app.cli import app as typer_app

if __name__ == "__main__":
    typer_app()
