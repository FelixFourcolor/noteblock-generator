from __future__ import annotations

from io import BytesIO
from pathlib import Path
from sys import stdin
from zipfile import ZipFile, is_zipfile

from msgspec import json

from .types import Building


def load(path: Path | None) -> Building | None:
    if not (src := _load_source(path)):
        return None

    if not (data := _read_source(src)):
        return None

    return json.decode(data, type=Building)


def _load_source(path: Path | None) -> Path | BytesIO | None:
    if path:
        return path

    if stdin.isatty():
        return None

    # prevent an infinite loop in case user does something like "yes | nbg"
    MAX_SIZE = 100 * 1024 * 1024  # 100 MB
    return BytesIO(stdin.buffer.read(MAX_SIZE))


def _read_source(src: Path | BytesIO) -> bytes | None:
    if is_zipfile(src):
        return _unzip(src)

    if isinstance(src, Path):
        return src.read_bytes()

    return src.getvalue()


def _unzip(src: Path | BytesIO) -> bytes:
    with ZipFile(src) as zf:
        files = [n for n in zf.namelist() if not n.endswith("/")]
        if len(files) != 1:
            raise ValueError
        return zf.read(files[0])
