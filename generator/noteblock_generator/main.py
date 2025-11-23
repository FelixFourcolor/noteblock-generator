from typer import Typer

from .cli.commands import run


def main():
    app = Typer(add_completion=False)
    app.command(no_args_is_help=True)(run)
    app()
