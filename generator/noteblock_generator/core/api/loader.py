from __future__ import annotations

import os
import time
from io import BytesIO
from pathlib import Path
from sys import stdin
from threading import Thread
from typing import Generator, Literal, overload
from zipfile import ZipFile, is_zipfile

from click import UsageError
from msgspec import DecodeError, json
from watchfiles import watch

from .types import Building

# prevent infinite loop on infinite input (like `yes | nbg`)
MAX_PIPE_SIZE = 100 * 1024 * 1024  # 100 MB


@overload
def load(path: Path | None) -> Building: ...


@overload
def load(path: Path | None, *, watch: Literal[True]) -> Generator[Building]: ...


def load(path: Path | None, *, watch: bool = False) -> Building | Generator[Building]:
    if not watch:
        src = _load_source(path)
        data = _read_source(src)
        return _decode(data)

    if path:
        return _load_on_change(path)
    else:
        return _load_stdin_stream()


def _load_on_change(path: Path) -> Generator[Building]:
    def trigger_initial_run():
        # Need a way to trigger the first read.
        # Alternative would be to call another generate() before the watch loop;
        # but then changes during the initial run would be missed.
        # Ugly but no other way.
        time.sleep(0.25)
        os.utime(path)

    trigger_thread = Thread(target=trigger_initial_run, daemon=True)
    trigger_thread.start()

    isFirstRun = True
    for _ in watch(path, debounce=0, rust_timeout=0):
        if isFirstRun:
            isFirstRun = False
            yield load(path)
        else:  # defensive for temporary invalid data
            try:
                yield load(path)
            except Exception:
                continue


def _load_stdin_stream() -> Generator[Building]:
    if stdin.isatty():
        raise UsageError(
            "Missing input: Either provide file path with --in, or pipe content to stdin.",
        )

    DELIMITER = b"\n"
    CHUNK_SIZE = 1024 * 1024  # 1 MB

    buffer = bytearray()
    while True:
        if DELIMITER not in buffer:
            chunk = b"\0"
            while chunk and DELIMITER not in chunk and len(buffer) < MAX_PIPE_SIZE:
                chunk = os.read(stdin.fileno(), CHUNK_SIZE)
                buffer.extend(chunk)

        if not buffer:
            continue

        building: Building | None = None
        while True:
            try:
                delimiter = buffer.index(DELIMITER)
            except ValueError:
                break

            payload = buffer[:delimiter]
            del buffer[: delimiter + 1]

            update = _decode(payload)
            if not building:
                building = update
            else:  # only need to update blocks; size doesn't matter for partial update
                building.blocks.update(update.blocks)

        if not building:
            raise UsageError("Input data does not match expected format.")
        yield building


def _decode(data: bytes | bytearray) -> Building:
    try:
        return json.decode(data, type=Building)
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
