from threading import Lock
from typing import final

import typer
from click import Abort
from rich.console import Console as _Console
from rich.panel import Panel


@final
class Console:
    @staticmethod
    def print(*args, **kwargs):
        with _capture_lock:
            if _is_capturing:
                _capture_buffer.append((args, kwargs))
                return
        _print(*args, **kwargs)

    @staticmethod
    def confirm(text: str, *, default: bool) -> bool:
        _start_capture()
        try:
            result = typer.confirm(text, default=default)
        except Abort:
            _stop_capture(flush=False)
            Console.info(
                "\nNo input received, used {choice} by default.",
                choice="Y" if default else "N",
            )
            _flush_capture()
            return default
        except Exception:
            _stop_capture(flush=True)
            raise
        else:
            _stop_capture(flush=True)
            return result

    @staticmethod
    def info(text: str, *, important=False, **kwargs):
        if kwargs:
            text = text.format(**{
                k: f"[bold blue]{v}[/bold blue]" for k, v in kwargs.items()
            })
        if important:
            Console.print(Panel(text, expand=False, border_style="blue"))
        else:
            Console.print(text, style="dim")

    @staticmethod
    def success(text: str, *, important=False, **kwargs):
        if not important:
            Console.print(text, style="green")
            return

        if kwargs:
            text = text.format(**{
                k: f"[bold green]{v}[/bold green]" for k, v in kwargs.items()
            })
        Console.print(Panel(text, expand=False, border_style="green"))

    @staticmethod
    def warn(text: str, *, important=False, **kwargs):
        if not important:
            Console.print(text, style="red")
            return

        if kwargs:
            text = text.format(**{
                k: f"[bold red]{v}[/bold red]" for k, v in kwargs.items()
            })
        Console.print(Panel(text, expand=False, border_style="red"))


_console = _Console()
_capture_lock = Lock()
_is_capturing = False
_capture_buffer: list[tuple[tuple, dict]] = []


def _print(*args, **kwargs):
    _console.print(*args, **kwargs)


def _start_capture():
    global _is_capturing

    with _capture_lock:
        _is_capturing = True


def _stop_capture(*, flush: bool):
    global _is_capturing

    with _capture_lock:
        _is_capturing = False
    if flush:
        _flush_capture()


def _flush_capture():
    global _capture_buffer

    if not _capture_buffer:
        return

    with _capture_lock:
        for args, kwargs in _capture_buffer:
            _print(*args, **kwargs)
        _capture_buffer = []
