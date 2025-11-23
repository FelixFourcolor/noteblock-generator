from collections import deque
from collections.abc import Iterable
from threading import Thread

from rich import progress

from .console import Console


class UserCancelled(Exception): ...


class ProgressBar:
    def __init__(self, *, cancellable: bool):
        if cancellable:
            self._thread = Thread(target=self._prompt_worker, daemon=True)
            self._user_response = None
        else:
            self._thread = None
            self._user_response = True  # non-cancellable = auto confirm yes

    def __enter__(self):
        if self._thread:
            self._thread.start()
        return self._track

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._thread:
            self._thread.join()

    def _prompt_worker(self):
        self._user_response = Console.confirm("Confirm to proceed?", default=True)

    def _track(
        self,
        jobs_iter: Iterable,
        *,
        description: str,
        jobs_count: int | None = None,
        transient=False,
    ):
        if not self.result_ready:
            for _ in jobs_iter:
                if jobs_count is not None:
                    jobs_count -= 1
                if self.result_ready:
                    break
            else:  #  all jobs finish before user responds
                if transient:
                    return

        if self.cancelled:
            raise UserCancelled

        deque(
            progress.track(
                jobs_iter,
                total=jobs_count,
                description=description,
                transient=transient,
                show_speed=False,
            ),
            maxlen=0,
        )

    @property
    def result_ready(self) -> bool:
        return self._user_response is not None

    @property
    def cancelled(self) -> bool:
        if not self._thread:
            return False

        self._thread.join()
        return not self._user_response
