from collections.abc import Iterable
from threading import Thread

from rich import progress

from .console import Console
from .iter import exhaust


class Progress:
    def __init__(self, cancellable: bool):
        if cancellable:
            self._thread = Thread(target=self._prompt_worker, daemon=True)
            self._user_response = None
        else:
            self._thread = None
            self._user_response = True  # non-cancellable = auto confirm yes

    def __enter__(self):
        if self._thread:
            self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._thread:
            self._thread.join()

    def _prompt_worker(self):
        self._user_response = Console.confirm("Confirm to proceed?", default=True)

    def run(
        self,
        jobs_iter: Iterable,
        *,
        jobs_count: int | None = None,
        description: str,
        transient=False,
    ) -> bool:
        if not self.result_ready:
            for _ in jobs_iter:
                if jobs_count is not None:
                    jobs_count -= 1
                if self.result_ready:
                    break
            else:  #  all jobs finish before user responds
                if transient:
                    return True

        if self.cancelled:
            return False

        exhaust(
            progress.track(
                jobs_iter,
                total=jobs_count,
                description=description,
                transient=transient,
                show_speed=False,
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
