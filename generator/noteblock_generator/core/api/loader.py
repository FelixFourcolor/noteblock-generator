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
        return _load(path, Building)

    def live_loader() -> Generator[Building]:
        data_stream = _file_stream(path) if path else _stdin_stream()
        is_first_run = True

        def refresh():
            if is_first_run:
                if path:
                    return next(data_stream)
                return Console.status("Compiling", data_stream.__next__)

            Console.newline()
            return Console.status("Waiting for changes", data_stream.__next__)

        while True:
            payload = refresh()
            is_first_run = False

            if payload.error:
                Console.warn(payload.error, important=True)
                continue
            if not payload.blocks or not payload.size:
                raise UsageError("Input data does not match expected format.")
            yield Building(blocks=payload.blocks, size=payload.size)

    return live_loader()


def _file_stream(path: Path) -> Generator[Payload]:
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

    is_first_run = True
    for _ in watch(path, debounce=0, rust_timeout=0):
        triggered = True
        try:
            yield _load(path, type=Payload)
            is_first_run = False
        except UsageError:
            # Ignore read errors on subsequent runs
            # because file may temporarily be in an invalid state
            if is_first_run:
                raise


def _stdin_stream() -> Generator[Payload]:
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

        # If multiple payloads come in one chunk, combine them
        payload: Payload | None = None
        while True:
            try:
                delimiter = buffer.index(DELIMITER)
            except ValueError:
                break

            chunk = buffer[:delimiter]
            del buffer[: delimiter + 1]
            update = _decode(chunk, Payload)

            if not payload:
                payload = update
                continue

            payload.error = update.error
            if update.blocks:
                if payload.blocks:
                    payload.blocks.update(update.blocks)
                else:
                    payload.blocks = update.blocks
            # no need to update size, it doesn't matter for partial updates

        if not payload:
            raise UsageError("Input data does not match expected format.")
        yield payload


T = TypeVar("T")


def _load(path: Path | None, type: type[T]) -> T:
    src = _load_source(path)
    data = _read_source(src)
    return _decode(data, type)


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
