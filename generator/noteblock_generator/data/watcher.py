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
        data = next(data_stream)
        Console.info(f"{'-' * 15} {time.strftime('%H:%M:%S')} {'-' * 15}")
        return data

    def fetch_next_with_status():
        if is_first_run:
            if path:
                return fetch_next()
            return Console.status("Compiling", fetch_next)
        Console.newline()
        return Console.status("Waiting for changes", fetch_next)

    while True:
        try:
            payload = fetch_next_with_status()
            is_first_run = False
        except StopIteration:
            break

        if payload.error is not None:
            Console.warn(text=payload.error, important=True)
            continue

        if payload.blocks is not None and payload.size is not None:
            yield Building(blocks=payload.blocks, size=payload.size)
            continue

        raise UsageError("Input data does not match expected format.")


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
                return
            buffer.extend(chunk)

        payloads = buffer.split(DELIMITER)
        buffer = payloads.pop()  # leftover partial payload

        combined_payload = Payload()
        for payload in [_decode(payload) for payload in payloads]:
            if payload.blocks is not None:
                if combined_payload.blocks is None:
                    combined_payload.blocks = payload.blocks
                else:
                    combined_payload.blocks |= payload.blocks
            if payload.size is not None:
                combined_payload.size = payload.size
            combined_payload.error = payload.error
        yield combined_payload


_decoder = json.Decoder(Payload)


def _decode(data: bytes | bytearray) -> Payload:
    try:
        return _decoder.decode(data)
    except DecodeError:
        raise UsageError("Input data does not match expected format.")
