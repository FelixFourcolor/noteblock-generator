from collections.abc import Callable
from functools import partial
from typing import TypeVar

import typer
from click import Abort
from rich.console import Console as _Console
from rich.panel import Panel

_console = _Console()
_print = partial(_console.print, highlight=False)

T = TypeVar("T")


class Console:
    @staticmethod
    def newline(count=1):
        for _ in range(count):
            _print()

    @staticmethod
    def confirm(text: str, *, default: bool) -> bool:
        try:
            return typer.confirm(text, default=default)
        except Abort:
            Console.info(
                "\nNo input received, used {choice} by default.",
                choice="Y" if default else "N",
                accent="green" if default else "red",
            )
            return default

    @staticmethod
    def info(text: str, *, important=False, accent="blue", **kwargs):
        if kwargs:
            text = text.format(**{
                k: f"[bold {accent}]{v}[/bold {accent}]" for k, v in kwargs.items()
            })
        if important:
            _print(Panel(text, expand=False, border_style=accent))
        else:
            _print(text, style="dim")

    @staticmethod
    def success(text: str, *, important=False, **kwargs):
        if kwargs:
            text = text.format(**{
                k: f"[bold green]{v}[/bold green]" for k, v in kwargs.items()
            })
        if important:
            _print(Panel(text, expand=False, border_style="green"))
        else:
            _print(text, style="dim green")

    @staticmethod
    def warn(text: str, *, important=False, **kwargs):
        if kwargs:
            text = text.format(**{
                k: f"[bold red]{v}[/bold red]" for k, v in kwargs.items()
            })
        if important:
            _print(Panel(text, expand=False, border_style="red"))
        else:
            _print(text, style="dim red")

    @staticmethod
    def status(text: str, callback: Callable[[], T]) -> T:
        style = "dim"
        with _console.status(
            f"[{style}]{text}[/{style}]",
            spinner="line",
            spinner_style=style,
            speed=0.5,
        ):
            return callback()
