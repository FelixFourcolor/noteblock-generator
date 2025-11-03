from collections.abc import Iterable
from threading import Thread
from typing import final

from rich import progress

from .console import Console
from .iter import exhaust


@final
class CancellableProgress:
    def __init__(self, text: str, *, default: bool):
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

    def run(
        self,
        jobs_iter: Iterable,
        *,
        jobs_count: int,
        description: str,
        cancellable=True,
    ) -> bool:
        if not self.result_ready:
            for _ in jobs_iter:
                jobs_count -= 1
                if self.result_ready:
                    break
            else:  #  all jobs finish before user responds
                if not cancellable:
                    return True

        if self.cancelled:
            return False

        exhaust(
            progress.track(
                jobs_iter,
                total=jobs_count,
                description=description,
                transient=not cancellable,
            )
        )
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
