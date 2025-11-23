from __future__ import annotations

import contextlib
import os
import secrets
import shutil
import signal
import tempfile
import time
import zlib
from pathlib import Path

from click import UsageError

from .. import APP_NAME
from ..cli.console import Console
from ..cli.progress_bar import UserCancelled
from .world import ChunkLoadError, World

_HANDLED_SIGNALS = set(signal.Signals) - {
    # uncatchable signals
    signal.SIGKILL,
    signal.SIGSTOP,
}


class IgnoreInterrupt:
    def __init__(self):
        self._original_handlers = {}

    def __enter__(self):
        self._original_handlers = {
            sig: signal.signal(sig, signal.SIG_IGN) for sig in _HANDLED_SIGNALS
        }
        return self

    def __exit__(self, exc_type, exc_value, tb):
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)


class GeneratingSession:
    def __init__(self, path: Path):
        self._original_path = path
        self._working_path: str | None = None
        self._world: World | None = None
        self._world_hash: int | None = None

    def load_world(self):
        if not self._working_path:
            # clone unsuccessful, must generate in-place
            Console.warn(
                "If you are inside the world, {highlighted}.",
                highlighted="exit now before proceeding",
                important=True,
            )
            if not Console.confirm("Confirm to proceed?", default=False):
                raise UserCancelled

        world_path = self._working_path or self._original_path
        self._world = World.load(world_path)
        return self._world

    def __enter__(self):
        self._world_hash = self._compute_hash()
        self._working_path = self._create_shadow_copy()
        self._setup_signal_handlers()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._cleanup(commit=exc_type is None)

        if exc_type is UserCancelled:
            os._exit(0)

        if isinstance(exc_value, ChunkLoadError):
            x, z = exc_value.coordinates
            Console.warn(
                "Failed to load chunk at {coordinates}.\n"
                + "Load the chunk at this position in-game and try again.",
                coordinates=f"({x=}, {z=})",
                important=True,
            )
            os._exit(1)

    def _setup_signal_handlers(self):
        def handle_interrupt(sig: int, _):
            Console.newline()
            self._cleanup(commit=False)
            os._exit(130 if sig == signal.SIGINT else 143)

        for sig in _HANDLED_SIGNALS:
            signal.signal(sig, handle_interrupt)

    def _compute_hash(self) -> int | None:
        try:
            return _hash_files(self._original_path)
        except FileNotFoundError:
            raise UsageError(f"World path '{self._original_path}' does not exist.")

    def _create_shadow_copy(self):
        try:
            return _backup_files(self._original_path)
        except PermissionError:
            raise UsageError(
                "Permission denied to read save files. "
                + "If the game is running, close it and try again.",
            )

    def _cleanup(self, *, commit: bool):
        if not self._working_path:
            return
        try:
            if commit:
                self._commit()
        finally:
            shutil.rmtree(self._working_path, ignore_errors=True)

    def _externally_modified(self) -> bool:
        try:
            return self._world_hash is None or self._world_hash != self._compute_hash()
        except FileNotFoundError:
            return True

    def _commit(self):
        if not self._world:
            return

        if self._externally_modified():
            Console.success(
                "It looks like you were inside the world while generating."
                + "\nExit and re-enter to see the result.",
                important=True,
            )

        self._world.close()
        with IgnoreInterrupt():
            # This section is critical but should be very fast (< 0.1s)
            # No need to handle signals, just ignore them
            if self._working_path:
                shutil.rmtree(self._original_path, ignore_errors=True)
                shutil.move(self._working_path, self._original_path)


def _backup_files(src: Path, patience: int = 5):
    class PermissionDenied(Exception): ...

    def copyfile(src: str, dst: str):
        try:
            return shutil.copy2(src, dst)
        except PermissionError as e:
            # windows locks this file, but no need to copy it, so just ignore
            if Path(src).name != "session.lock":
                # PermissionError raised here will be
                # propagated by shutil.copytree as OSError, which is not helpful.
                # So raise this custom exception instead.
                raise PermissionDenied(f"{src}: {e}")

    def copy(src: str, dst: str):
        src_path = Path(src)
        if src_path.is_dir():
            shutil.copytree(src, dst, copy_function=copyfile)
        elif src_path.is_file():
            copyfile(src, dst)

    temp_dir = Path(tempfile.gettempdir()) / APP_NAME
    temp_dir.mkdir(exist_ok=True)

    name = Path(src).name
    for _ in range(patience):
        try:
            copy(str(src), str(dst := temp_dir / name))
        except FileExistsError:
            name += f"_{secrets.token_hex(3)}"
        except PermissionDenied as e:
            raise PermissionError(e)
        else:
            return str(dst)


def _hash_files(src: Path) -> int | None:
    deadline = time.monotonic() + 2

    def check_time():
        if time.monotonic() >= deadline:
            raise TimeoutError

    def update(src: Path, hash: int) -> int:
        hash = zlib.crc32(src.name.encode(), hash)
        if src.is_file():
            return update_file(src, hash)
        if src.is_dir():
            return update_dir(src, hash)
        return hash

    READ_CHUNK = 16 * 1024

    def update_file(src: Path, hash: int) -> int:
        with src.open("rb") as f:
            for chunk in iter(lambda: f.read(READ_CHUNK), b""):
                check_time()
                hash = zlib.crc32(chunk, hash)

        return hash

    def update_dir(src: Path, hash: int) -> int:
        for path in sorted(src.iterdir(), key=lambda p: str(p)):
            check_time()
            hash = update(path, hash)
        return hash

    with contextlib.suppress(PermissionError):
        if not src.exists():
            raise FileNotFoundError()
        try:
            return update(src, 0)
        except TimeoutError:
            return None
