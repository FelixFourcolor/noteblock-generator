from collections.abc import Iterable
from threading import Thread

import typer
from click import Abort
from rich.console import Console as _Console
from rich.panel import Panel
from rich.progress import track

_console = _Console()
_print = _console.print


class Console:
    @staticmethod
    def newline():
        _print()

    @staticmethod
    def confirm(text, *, default: bool | None) -> bool:
        try:
            return typer.confirm(text, default=default)
        except Abort:
            Console.info(
                "\nNo input received, used {choice} by default.",
                choice="Y" if default else "N",
            )
            return default or False

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
        if not important:
            _print(text, style="green")
            return

        if kwargs:
            text = text.format(**{
                k: f"[bold green]{v}[/bold green]" for k, v in kwargs.items()
            })
        _print(Panel(text, expand=False, border_style="green"))

    @staticmethod
    def warn(text: str, *, important=False, **kwargs):
        if not important:
            _print(text, style="red")
            return

        if kwargs:
            text = text.format(**{
                k: f"[bold red]{v}[/bold red]" for k, v in kwargs.items()
            })
        _print(Panel(text, expand=False, border_style="red"))


class CancellableProgress:
    def __init__(self, text: str, *, default: bool | None):
        self.text = text
        self.default = default

        self._thread: Thread | None = None
        self._user_response: bool | None = None

    def __enter__(self):
        self._thread = Thread(target=self._input_worker, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._thread:
            self._thread.join()

    def run(self, jobs_iter: Iterable, jobs_count: int, description: str) -> bool:
        if not self.result_ready:
            for _ in jobs_iter:
                jobs_count -= 1
                if self.result_ready:
                    break

        if self.cancelled:
            return False

        if not jobs_count:
            jobs_iter = range(1)
            jobs_count = 1

        for _ in track(
            jobs_iter,
            total=jobs_count,
            description=description,
        ):
            pass

        return True

    @property
    def result_ready(self) -> bool:
        return self._user_response is not None

    @property
    def cancelled(self) -> bool:
        if not self._thread:
            return False

        self._thread.join()
        return not self._user_response

    def _input_worker(self):
        self._user_response = Console.confirm(self.text, default=self.default)
