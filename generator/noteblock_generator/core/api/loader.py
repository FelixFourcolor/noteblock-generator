from __future__ import annotations

from io import BytesIO
from pathlib import Path
from sys import stdin
from typing import TypeVar
from zipfile import ZipFile, is_zipfile

from click import UsageError
from msgspec import DecodeError, json

from .types import Building

# prevent infinite loop on infinite input (like `yes | nbg`)
MAX_PIPE_SIZE = 100 * 1024 * 1024  # 100 MB


def load(path: Path | None):
    src = _load_source(path)
    data = _read_source(src)
    return decode(data, Building)


T = TypeVar("T")


def decode(data: bytes | bytearray, type: type[T]) -> T:
    try:
        return json.decode(data, type=type)
    except DecodeError:
        raise UsageError("Input data does not match expected format.")


def _load_source(path: Path | None) -> Path | BytesIO:
    if path:
        return path

    if stdin.isatty():
        raise UsageError(
            "Missing input: Either provide file path with --in, or pipe content to stdin.",
        )

    return BytesIO(stdin.buffer.read(MAX_PIPE_SIZE))


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
            raise UsageError("Input data does not match expected format.")
        return zf.read(files[0])
