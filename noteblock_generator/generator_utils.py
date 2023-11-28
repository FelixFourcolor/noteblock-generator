from __future__ import annotations

import _thread
import contextlib
import logging
import os
import shutil
import signal
import sys
import tempfile
import zlib
from enum import Enum
from functools import partial
from io import StringIO
from multiprocessing import Process, Queue
from pathlib import Path
from threading import Thread
from typing import Callable, Generic, Optional, TypeVar

from .cli import logger

# make output consistent for pipes vs tty inputs
if not sys.stdin.isatty():
    _input = input

    def input(__prompt="", /):  # noqa: A001
        print(out := _input(__prompt))
        return out


class Direction(tuple[int, int], Enum):
    # coordinates in (x, z)
    north = (0, -1)
    south = (0, 1)
    east = (1, 0)
    west = (-1, 0)

    def __str__(self):
        return self.name

    def __mul__(self, other: tuple[int, int]) -> tuple[int, int]:
        """Complex multiplication, with (x, z) representing x + zi"""
        return (
            self[0] * other[0] - self[1] * other[1],
            self[0] * other[1] + self[1] * other[0],
        )

    def __neg__(self):
        # negation is multiplying with 0i - 1, which is west
        return Direction(self * Direction.west)


def terminal_width():
    return min(80, os.get_terminal_size()[0] - 1)


def progress_bar(progress: int, total: int, *, text: str):
    ratio = progress / total
    percentage = f" {100*ratio:.0f}% "

    alignment_spacing = " " * (6 - len(percentage))
    total_length = max(0, terminal_width() - len(text) - 8)
    fill_length = int(total_length * ratio)
    finished_portion = "#" * fill_length
    remaining_portion = "-" * (total_length - fill_length)
    progress_bar = f"[{finished_portion}{remaining_portion}]" if total_length else ""
    end_of_line = "" if ratio == 1 else "\033[F"

    logger.info(f"{text}{alignment_spacing}{percentage}{progress_bar}{end_of_line}")


class UserPrompt:
    """Run a user prompt, optionally in a non-blocking thread."""

    def __init__(self, prompt: str, yes: tuple[str, ...], *, blocking: bool):
        self._prompt = prompt
        self._yes = yes
        if blocking:
            self._run()
        else:
            self._thread = Thread(target=self._run, daemon=True)
            self._thread.start()

    def _run(self):
        # capture logs to not interrupt the user prompt
        logging.basicConfig(format="%(message)s", stream=(bf := StringIO()), force=True)
        # prompt
        response = input(f"\033[33m{self._prompt} \033[m").lower().strip()
        yes = response in self._yes or not self._yes
        # stop capturing
        logging.basicConfig(format="%(message)s", force=True)

        if yes:
            # release captured logs
            print(bf.getvalue(), end="")
        else:
            _thread.interrupt_main()

    def wait(self):
        with contextlib.suppress(AttributeError):
            self._thread.join()

    @classmethod
    def debug(cls, prompt: str, yes: tuple[str, ...], *, blocking: bool):
        if logger.isEnabledFor(logging.DEBUG):
            return cls(prompt=prompt, yes=yes, blocking=blocking)

    @classmethod
    def warning(cls, prompt: str, yes: tuple[str, ...], *, blocking: bool):
        if logger.isEnabledFor(logging.WARNING):
            return cls(prompt=prompt, yes=yes, blocking=blocking)


def _hash_files(src: str | Path) -> Optional[int]:
    def update(src: Path, _hash) -> int:
        _hash = zlib.crc32(src.name.encode(), _hash)
        if src.is_file():
            return update_file(src, _hash)
        if src.is_dir():
            return update_dir(src, _hash)
        return _hash

    def update_file(src: Path, _hash) -> int:
        with src.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                _hash = zlib.crc32(chunk, _hash)
        return _hash

    def update_dir(src: Path, _hash) -> int:
        for path in sorted(src.iterdir(), key=lambda p: str(p)):
            _hash = update(path, _hash)
        return _hash

    with contextlib.suppress(PermissionError):
        if not (src := Path(src)).exists():
            raise FileNotFoundError()
        return update(src, 0)


def hash_files(src: str | Path) -> Optional[int]:
    """Hash src (file or directory), return None if unable to."""
    with contextlib.suppress(_TimeoutError):
        return _timeout(partial(_hash_files, src), timeout=2)


def _backup_files(src: str):
    class PermissionDenied(Exception):
        """PermissionError raised inside safe_copy
        will be propagated by shutil.copytree as OSError, which is not helpful.
        So raise this instead.
        """

    def copyfile(src: str, dst: str):
        try:
            return shutil.copy2(src, dst)
        except PermissionError as e:
            # This isn't a problem for linux, but windows raises PermissionError
            # if we try to read the save folder while the game is running.
            # The only file I know that does this is "session.lock", and
            # it's also the only file I know that can be deleted without losing data.
            # Therefore, if "session.lock" raises PermissionError, ignore it,
            # otherwise propagate the error to the user.
            if Path(src).name != "session.lock":
                raise PermissionDenied(f"{src}: {e}")

    def copy(src: str, dst: str):
        _src = Path(src)
        if _src.is_dir():
            shutil.copytree(src, dst, copy_function=copyfile)
        elif _src.is_file():
            copyfile(src, dst)

    temp_dir = Path(tempfile.gettempdir()) / "noteblock-generator"
    name = Path(src).name
    i = 0
    while True:
        try:
            copy(src, str(dst := temp_dir / name))
        except FileExistsError:
            if name.endswith(suffix := f" ({i})"):
                name = name[: -len(suffix)]
            name += f" ({(i := i + 1)})"
        except PermissionDenied as e:
            raise PermissionError(e)
        else:
            return str(dst)


def backup_files(src: str) -> Optional[str]:
    """Copy src (file or directory) to a temp directory.
    Automatically resolve name by appending (1), (2), etc.
    Return the chosen name; or None if unable to.
    """
    with contextlib.suppress(_TimeoutError):
        return _timeout(partial(_backup_files, src), timeout=2)


class PreventKeyboardInterrupt:
    """Place any code inside "with PreventKeyboardInterrupt(): ..."
    to prevent keyboard interrupt
    """

    def __enter__(self):
        self.handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

    def __exit__(self, exc_type, exc_value, tb):
        signal.signal(signal.SIGINT, self.handler)


_T = TypeVar("_T")


class _Result(Generic[_T]):
    ok: _T
    err: Optional[Exception] = None


class _TimeoutError(Exception):
    pass


def _timeout_func_wrapper(target: Callable, queue: Queue):
    result = queue.get()
    try:
        result.ok = target()
    except Exception as e:
        result.err = e
    queue.put(result)


def _timeout(target: Callable[[], _T], *, timeout: float) -> _T:
    (queue := Queue()).put(_Result[_T]())
    (process := Process(target=_timeout_func_wrapper, args=[target, queue])).start()
    process.join(timeout=timeout)

    if process.is_alive():
        process.kill()
        raise _TimeoutError

    if (err := (result := queue.get()).err) is not None:
        raise err
    return result.ok
