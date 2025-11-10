from __future__ import annotations

from io import BytesIO
from pathlib import Path
from sys import stdin
from zipfile import ZipFile, is_zipfile

from click import UsageError
from msgspec import json

from .types import Building


def load(path: Path | None) -> Building:
    try:
        if src := _load_source(path):
            data = _read_source(src)
            return json.decode(data, type=Building)
    except Exception:
        raise UsageError("Error reading input data.")

    raise UsageError(
        "Missing input: Either provide file path with --in, or pipe content to stdin.",
    )


def _load_source(path: Path | None) -> Path | BytesIO | None:
    if path:
        return path

    if stdin.isatty():
        return None

    # prevent an infinite loop in case user does something like "yes | nbg"
    MAX_SIZE = 100 * 1024 * 1024  # 100 MB
    return BytesIO(stdin.buffer.read(MAX_SIZE))


def _read_source(src: Path | BytesIO) -> bytes:
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
