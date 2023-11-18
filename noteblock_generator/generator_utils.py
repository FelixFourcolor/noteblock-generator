from __future__ import annotations

import _thread
import hashlib
import logging
import os
import shutil
import signal
import tempfile
from enum import Enum
from io import StringIO
from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING, Optional, TypeVar

from .cli import logger

if TYPE_CHECKING:
    from hashlib import _Hash as Hash


class Direction(tuple[int, int], Enum):
    """Minecraft's cardinal direction"""

    # coordinates in (x, z)
    north = (0, -1)
    south = (0, 1)
    east = (1, 0)
    west = (-1, 0)

    def __str__(self):
        return self.name

    def __mul__(self, other: DirectionType) -> DirectionType:
        """Complex multiplication, withy (x, z) representing xi + z"""

        return type(other)(
            (
                self[0] * other[1] + self[1] * other[0],
                self[1] * other[1] - self[0] * other[0],
            )
        )

    def __neg__(self):
        # negation is multiplying with 0i - 1, which is north
        return self * Direction.north


DirectionType = TypeVar("DirectionType", Direction, tuple[int, int])


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
    def __init__(self, prompt: str, yes: tuple[str], *, blocking: bool):
        self._prompt = prompt
        self._yes = yes
        if blocking:
            self._run()
        else:
            self._thread = Thread(target=self._run, daemon=True)
            self._thread.start()

    def _run(self):
        # capture logs to not interrupt the user prompt
        logging.basicConfig(
            format="%(message)s", stream=(buffer := StringIO()), force=True
        )
        # prompt
        result = input(f"\033[33m{self._prompt}\033[m").lower().strip() in self._yes
        # stop capturing
        logging.basicConfig(format="%(message)s", force=True)

        if result:
            # release captured logs
            print(f"\n{buffer.getvalue()}", end="")
        else:
            _thread.interrupt_main()

    def wait(self):
        self._thread.join()

    @classmethod
    def debug(cls, *args, **kwargs):
        if logger.isEnabledFor(logging.DEBUG):
            return cls(*args, **kwargs)

    @classmethod
    def info(cls, *args, **kwargs):
        if logger.isEnabledFor(logging.INFO):
            return cls(*args, **kwargs)

    @classmethod
    def warning(cls, *args, **kwargs):
        if logger.isEnabledFor(logging.WARNING):
            return cls(*args, **kwargs)

    @classmethod
    def error(cls, *args, **kwargs):
        if logger.isEnabledFor(logging.ERROR):
            return cls(*args, **kwargs)

    @classmethod
    def critical(cls, *args, **kwargs):
        if logger.isEnabledFor(logging.CRITICAL):
            return cls(*args, **kwargs)


def get_hash(src: str | Path) -> Optional[bytes]:
    """Hash src (file or directory), return None if unable to."""

    def update(src: Path, _hash: Hash) -> Hash:
        _hash.update(src.name.encode())
        return update_file(src, _hash) if src.is_file() else update_dir(src, _hash)

    def update_file(src: Path, _hash: Hash) -> Hash:
        with src.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                _hash.update(chunk)
        return _hash

    def update_dir(src: Path, _hash: Hash) -> Hash:
        for path in sorted(src.iterdir(), key=lambda p: str(p)):
            _hash = update(path, _hash)
        return _hash

    try:
        return update(Path(src), hashlib.blake2b()).digest()
    except PermissionError:
        return


def backup(src: str) -> str:
    """Copy src (file or directory) to a temp directory.
    Automatically resolve name by appending (1), (2), etc.
    Return the chosen name.
    """

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
        if Path(src).is_file():
            copyfile(src, dst)
        else:
            shutil.copytree(src, dst, copy_function=copyfile)

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


class PreventKeyboardInterrupt:
    """Place any code inside "wibth PreventKeyboardInterrupt(): ..."
    to prevent keyboard interrupt
    """

    def __enter__(self):
        self.handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

    def __exit__(self, exc_type, exc_value, tb):
        signal.signal(signal.SIGINT, self.handler)
