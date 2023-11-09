# Copyright Felix Fourcolor 2023. CC0-1.0 license

from __future__ import annotations

import _thread
import hashlib
import logging
import os
import shutil
import signal
from enum import Enum
from io import StringIO
from pathlib import Path
from threading import Thread
from typing import Iterable, TypeVar

# Copyright Jonathan Hartley 2013. BSD 3-Clause license.
import colorama

# Copyright (c) 2010-202x The platformdirs developers. MIT license.
from platformdirs import user_cache_dir

from .main import logger


class Direction(tuple[int, int], Enum):
    """Minecraft's cardinal direction"""

    # coordinates in (x, z)
    north = (0, -1)
    south = (0, 1)
    east = (1, 0)
    west = (-1, 0)

    def __str__(self):
        return self.name

    # Operator overloading
    # -----------------------------------------------------------------------------
    # Multiplication
    # with another Direction: like complex multiplication, return a Direction
    # with a tuple: like complex multiplication, return a tuple
    # with an int: multiply our non-zero component with the int, return an int

    def __mul__(self, other: _DirectionType) -> _DirectionType:
        if isinstance(other, Direction):
            return Direction(
                (
                    self[0] * other[1] + self[1] * other[0],
                    self[1] * other[1] - self[0] * other[0],
                )
            )
        if isinstance(other, tuple):
            return (
                self[0] * other[1] + self[1] * other[0],
                self[1] * other[1] - self[0] * other[0],
            )
        if isinstance(other, int):
            return max(self, key=abs) * other
        return NotImplemented

    def __rmul__(self, other: _DirectionType) -> _DirectionType:
        return self * other

    def __neg__(self):
        # negation is like multiplying with 0i - 1, which is north
        return self * Direction.north

    # -----------------------------------------------------------------------------
    # Addition and subtraction
    # with a tuple: like complex addition and subtraction, return a tuple
    # with an int: add/subtract our non-zero component with the int, return an int

    def __add__(self, other: _NumType) -> _NumType:
        if isinstance(other, tuple):
            return (self[0] + other[0], self[1] + other[1])
        if isinstance(other, int):
            return max(self, key=abs) + other
        return NotImplemented

    def __radd__(self, other: _NumType) -> _NumType:
        return self + other

    def __sub__(self, other: _NumType) -> _NumType:
        if isinstance(other, tuple):
            return (self[0] - other[0], self[1] - other[1])
        if isinstance(other, int):
            return max(self, key=abs) - other
        return NotImplemented

    def __rsub__(self, other: _NumType) -> _NumType:
        return -self + other

    # -----------------------------------------------------------------------------
    # bool: whether the non-zero component is positive

    def __bool__(self):
        return max(self, key=abs) > 0


_DirectionType = TypeVar("_DirectionType", Direction, tuple[int, int], int)
_NumType = TypeVar("_NumType", tuple[int, int], int)


TERMINAL_WIDTH = min(80, os.get_terminal_size()[0])

# Enable ANSI escape code on Windows PowerShell for the progress bar
colorama.just_fix_windows_console()


def progress_bar(iteration: float, total: float, *, text: str):
    ratio = iteration / total
    percentage = f" {100*ratio:.0f}% "

    alignment_spacing = " " * (6 - len(percentage))
    total_length = max(0, TERMINAL_WIDTH - len(text) - 16)
    fill_length = int(total_length * ratio)
    finished_portion = "#" * fill_length
    remaining_portion = "-" * (total_length - fill_length)
    progress_bar = f"[{finished_portion}{remaining_portion}]" if total_length else ""
    end_of_line = "" if ratio == 1 else "\033[F"

    logger.info(f"{text}{alignment_spacing}{percentage}{progress_bar}{end_of_line}")


class UserPrompt:
    def __init__(self, prompt: str, choices: Iterable[str], *, blocking: bool):
        self._prompt = prompt
        self._choices = choices
        self._thread = Thread(target=self._run, daemon=True)
        if blocking:
            self._thread.run()
        else:
            self._thread.start()

    def _run(self):
        # capture logs to not interrupt the user prompt
        logging.basicConfig(
            format="%(levelname)s - %(message)s",
            stream=(buffer := StringIO()),
            force=True,
        )
        # prompt
        result = input(self._prompt).lower() in self._choices
        # stop capturing
        logging.basicConfig(format="%(levelname)s - %(message)s", force=True)

        if result:
            # release captured logs
            print(f"\n{buffer.getvalue()}", end="")
        else:
            _thread.interrupt_main()

    def wait(self):
        self._thread.join()


def hash_directory(directory: str | Path):
    def update(directory: str | Path, _hash: hashlib._Hash) -> hashlib._Hash:
        for path in sorted(Path(directory).iterdir(), key=lambda p: str(p)):
            _hash.update(path.name.encode())
            if path.is_file():
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        _hash.update(chunk)
            elif path.is_dir():
                _hash = update(path, _hash)
        return _hash

    return update(directory, hashlib.blake2b()).digest()


def backup_directory(src: Path, *args, **kwargs) -> Path:
    """Copy directory to user's cache dir,
    automatically resolve name if direcotry already exists by appending (1), (2), etc. to the end.
    Return the chosen name.
    """

    cache_dir = Path(user_cache_dir("noteblock-generator"))
    name = src.stem
    i = 0
    while True:
        try:
            shutil.copytree(src, (dst := cache_dir / name), *args, **kwargs)
        except FileExistsError:
            if name.endswith(suffix := f" ({i})"):
                name = name[: -len(suffix)]
            name += f" ({(i := i + 1)})"
        else:
            return dst


class PreventKeyboardInterrupt:
    """Place any code inside "with PreventKeyboardInterrupt(): ..."
    to prevent keyboard interrupt
    """

    def __enter__(self):
        self.handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

    def __exit__(self, exc_type, exc_value, tb):
        signal.signal(signal.SIGINT, self.handler)
