from collections import deque
from collections.abc import Generator
from threading import Thread
from typing import TypeVar

from rich import progress

from .console import Console

T = TypeVar("T")


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
        jobs_iter: Generator[object, None, T],
        *,
        description: str,
        jobs_count: int | None = None,
        transient=False,
    ) -> T:
        result: list[T] = []

        def capture_return():
            try:
                while True:
                    yield next(jobs_iter)
            except StopIteration as e:
                result.append(e.value)

        jobs_iter_wrapper = capture_return()

        if not self.result_ready:
            for _ in jobs_iter_wrapper:
                if jobs_count is not None:
                    jobs_count -= 1
                if self.result_ready:
                    break
            else:  #  all jobs finish before user responds
                if transient:
                    return result[0]

        if self.cancelled:
            raise UserCancelled

        deque(
            progress.track(
                jobs_iter_wrapper,
                total=jobs_count,
                description=description,
                transient=transient,
                show_speed=False,
            ),
            maxlen=0,
        )

        return result[0]

    @property
    def result_ready(self) -> bool:
        return self._user_response is not None

    @property
    def cancelled(self) -> bool:
        if not self._thread:
            return False

        self._thread.join()
        return not self._user_response
