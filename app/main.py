# pylint: disable=unused-import

# noinspection PyUnusedImports
import app.controller.commands.clients # pyright: ignore[reportUnusedImport]
# noinspection PyUnusedImports
import app.controller.commands.configure # pyright: ignore[reportUnusedImport]
# noinspection PyUnusedImports
import app.controller.commands.outbound # pyright: ignore[reportUnusedImport]
# noinspection PyUnusedImports
import app.controller.commands.routing # pyright: ignore[reportUnusedImport]
# noinspection PyUnusedImports
import app.controller.commands.state # pyright: ignore[reportUnusedImport]
from app.cli import app as typer_app

if __name__ == "__main__":
    typer_app()
