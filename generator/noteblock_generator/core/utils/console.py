from typing import final

import typer
from click import Abort
from rich.console import Console as _Console
from rich.panel import Panel

_console = _Console()


@final
class Console:
    @staticmethod
    def newline():
        _console.print()

    @staticmethod
    def clear():
        _console.clear()

    @staticmethod
    def confirm(text: str, *, default: bool) -> bool:
        try:
            return typer.confirm(text, default=default)
        except Abort:
            Console.info(
                "\nNo input received, used {choice} by default.",
                choice="Y" if default else "N",
            )
            return default

    @staticmethod
    def info(text: str, *, important=False, **kwargs):
        if kwargs:
            text = text.format(**{
                k: f"[bold blue]{v}[/bold blue]" for k, v in kwargs.items()
            })
        if important:
            _console.print(Panel(text, expand=False, border_style="blue"))
        else:
            _console.print(text, style="dim")

    @staticmethod
    def success(text: str, *, important=False, **kwargs):
        if not important:
            _console.print(text, style="green")
            return

        if kwargs:
            text = text.format(**{
                k: f"[bold green]{v}[/bold green]" for k, v in kwargs.items()
            })
        _console.print(Panel(text, expand=False, border_style="green"))

    @staticmethod
    def warn(text: str, *, important=False, **kwargs):
        if not important:
            _console.print(text, style="red")
            return

        if kwargs:
            text = text.format(**{
                k: f"[bold red]{v}[/bold red]" for k, v in kwargs.items()
            })
        _console.print(Panel(text, expand=False, border_style="red"))
