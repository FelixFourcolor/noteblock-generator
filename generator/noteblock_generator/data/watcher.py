from __future__ import annotations

import os
import time
from pathlib import Path
from sys import stdin
from threading import Thread
from typing import Generator

import watchfiles
from click import UsageError
from msgspec import DecodeError, json

from ..cli.console import Console
from .loader import MAX_PIPE_SIZE
from .schema import Building, Payload


def watch(path: Path | None) -> Generator[Building]:
    data_stream = _file_stream(path) if path else _stdin_stream()
    is_first_run = True

    def fetch_next():
        if is_first_run:
            if path:
                return next(data_stream)
            return Console.status("Compiling", data_stream.__next__)

        Console.newline()
        return Console.status("Waiting for changes", data_stream.__next__)

    while True:
        payload = fetch_next()
        is_first_run = False

        if payload.error:
            Console.warn(payload.error, important=True)
            continue

        if not payload.blocks or not payload.size:
            raise UsageError("Input data does not match expected format.")

        yield Building(blocks=payload.blocks, size=payload.size)


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
    for _ in watchfiles.watch(path, debounce=0, rust_timeout=0):
        triggered = True
        try:
            yield _decode(path.read_bytes())
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
            update = _decode(chunk)

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


_decoder = json.Decoder(Payload)


def _decode(data: bytes | bytearray) -> Payload:
    try:
        return _decoder.decode(data)
    except DecodeError:
        raise UsageError("Input data does not match expected format.")
