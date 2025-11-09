import typer
from click import Abort
from rich.console import Console as _Console
from rich.panel import Panel

_print = _Console().print


class Console:
    @staticmethod
    def newline():
        _print()

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
            _print(Panel(text, expand=False, border_style="blue"))
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
