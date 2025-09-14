from __future__ import annotations

from pathlib import Path
from sys import stdin

from pydantic import TypeAdapter

from .types import BuildingDTO


def load_and_validate(path: Path | None) -> BuildingDTO | None:
    if data := _load(path):
        schema = TypeAdapter(BuildingDTO)
        return schema.validate_json(data)


def _load(path: Path | None) -> bytes | None:
    if path:
        with path.open("rb") as f:
            return f.read()

    if not stdin.isatty():
        MAX_SIZE = 100 * 1024 * 1024  # 100MB
        return stdin.buffer.read(MAX_SIZE)
