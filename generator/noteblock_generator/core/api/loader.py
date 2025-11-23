from __future__ import annotations

import os
import time
from io import BytesIO
from pathlib import Path
from sys import stdin
from threading import Thread
from typing import Generator, Literal, TypeVar, overload
from zipfile import ZipFile, is_zipfile

from click import UsageError
from msgspec import DecodeError, json
from watchfiles import watch

from ..utils.console import Console
from .types import Building, Payload

# prevent infinite loop on infinite input (like `yes | nbg`)
MAX_PIPE_SIZE = 100 * 1024 * 1024  # 100 MB


@overload
def load(path: Path | None) -> Building: ...
@overload
def load(path: Path | None, *, watch: Literal[True]) -> Generator[Building]: ...
def load(path: Path | None, *, watch: bool = False):
    if not watch:
        src = _load_source(path)
        data = _read_source(src)
        return _decode(data, Building)
    elif path:
        return _load_on_change(path)
    else:
        return _load_stdin_stream()


def _load_on_change(path: Path) -> Generator[Building]:
    def trigger_initial_run():
        # Need a way to trigger the first run.
        # Only alternative to yield once before the watch loop;
        # but then changes during the initial run would be missed.
        while not triggered:
            time.sleep(0.2)
            os.utime(path)

    triggered = False
    trigger_thread = Thread(target=trigger_initial_run, daemon=True)
    trigger_thread.start()

    isFirstRun = True
    for _ in watch(path, debounce=0, rust_timeout=0):
        triggered = True
        try:
            yield load(path)
            isFirstRun = False
        except UsageError:
            # Ignore read errors on subsequent runs
            # because file may temporarily be in an invalid state
            if isFirstRun:
                raise


def _load_stdin_stream() -> Generator[Building]:
    if stdin.isatty():
        raise UsageError(
            "Missing input: Either provide file path with --in, or pipe content to stdin.",
        )

    DELIMITER = b"\n"
    CHUNK_SIZE = 1024 * 1024  # 1 MB

    buffer = bytearray()
    while True:
        chunk = b""
        while DELIMITER not in chunk and len(buffer) < MAX_PIPE_SIZE:
            chunk = os.read(stdin.fileno(), CHUNK_SIZE)
            if not chunk:
                raise UsageError("Input pipe closed.")
            buffer.extend(chunk)

        # If multiple updates come in one chunk, combine them
        payload: Payload | None = None
        while True:
            try:
                delimiter = buffer.index(DELIMITER)
            except ValueError:
                break

            chunk = buffer[:delimiter]
            del buffer[: delimiter + 1]
            payload_chunk = _decode(chunk, Payload)

            if not payload:
                payload = payload_chunk
            elif payload_chunk.error:
                payload.error = payload_chunk.error
            elif payload.blocks and payload_chunk.blocks:
                # only need to update blocks; size doesn't matter for partial updates
                payload.blocks.update(payload_chunk.blocks)

        if payload:
            if payload.error:
                Console.warn(payload.error, important=True)
                Console.newline()
            elif payload.blocks and payload.size:
                yield Building(blocks=payload.blocks, size=payload.size)

        raise UsageError("Input data does not match expected format.")


T = TypeVar("T")


def _decode(data: bytes | bytearray, type: type[T]) -> T:
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
