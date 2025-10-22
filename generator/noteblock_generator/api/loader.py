from __future__ import annotations

from pathlib import Path
from sys import stdin

from msgspec import json

from .types import BuildingDTO


def load_and_validate(path: Path | None) -> BuildingDTO | None:
    if data := _load(path):
        return json.decode(data, type=BuildingDTO)


def _load(path: Path | None) -> bytes | None:
    if path:
        with path.open("rb") as f:
            return f.read()

    if not stdin.isatty():
        # prevent infinite loop if user does something like `yes | nbg`
        MAX_SIZE = 100 * 1024 * 1024  # 100 MB
        return stdin.buffer.read(MAX_SIZE)
