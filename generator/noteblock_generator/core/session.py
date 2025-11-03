from __future__ import annotations

import os
import shutil
import signal
from pathlib import Path
from typing import final

from click import UsageError

from .utils.console import Console
from .utils.files import backup_files, hash_files
from .world import ChunkLoadError, World


class UserCancelled(Exception): ...


_HANDLED_SIGNALS = set(signal.Signals) - {
    # uncatchable signals
    signal.SIGKILL,
    signal.SIGSTOP,
}


@final
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


cancelled_message = "Generation cancelled. No changes were made."


@final
class GeneratingSession:
    def __init__(self, path: Path):
        self.original_path = path
        self.working_path: str | None = None
        self.world: World | None = None
        self.world_hash: int | None = None

    def load_world(self):
        if not self.working_path:
            # clone unsuccessful, must generate in-place
            Console.warn(
                "To prevent data corruption, if you are inside the world,\n{highlighted}.",
                highlighted="exit now before proceeding",
                important=True,
            )
            if not Console.confirm("Confirm to proceed?", default=False):
                raise UserCancelled

        world_path = self.working_path or self.original_path
        self.world = World.load(world_path)
        return self.world

    def __enter__(self):
        self.world_hash = self._compute_hash()
        self.working_path = self._create_shadow_copy()
        self._setup_signal_handlers()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._cleanup(commit=exc_type is None)

        if exc_type is UserCancelled:
            Console.success(cancelled_message)
            os._exit(0)

        if isinstance(exc_value, ChunkLoadError):
            Console.warn(
                "Failed to load chunk at {coordinates}.\n"
                + "Load the chunk at this position in-game and try again.",
                coordinates=exc_value.coordinates,
                important=True,
            )
            os._exit(1)

    def _setup_signal_handlers(self):
        def handle_interrupt(sig: int, _):
            Console.print()
            self._cleanup(commit=False)
            os._exit(130 if sig == signal.SIGINT else 143)

        for sig in _HANDLED_SIGNALS:
            signal.signal(sig, handle_interrupt)

    def _compute_hash(self) -> int | None:
        try:
            return hash_files(self.original_path)
        except FileNotFoundError:
            raise UsageError(f"World path '{self.original_path}' does not exist.")

    def _create_shadow_copy(self):
        try:
            return backup_files(self.original_path)
        except PermissionError:
            raise UsageError(
                "Permission denied to read save files. "
                + "If the game is running, close it and try again.",
            )

    def _cleanup(self, *, commit: bool):
        if not self.working_path:
            return
        try:
            if commit:
                self._commit()
        finally:
            shutil.rmtree(self.working_path, ignore_errors=True)

    def _externally_modified(self) -> bool:
        try:
            return self.world_hash is None or self.world_hash != self._compute_hash()
        except FileNotFoundError:
            return True

    def _commit(self):
        if not self.world:
            return

        if self._externally_modified():
            Console.success(
                "It looks like you were inside the world while generating.\n"
                + "Exit and re-enter to see the result."
            )

        self.world.close()
        with IgnoreInterrupt():
            # This section is critical but should be very fast (< 0.1s)
            # No need to handle signals, just ignore them
            if self.working_path:
                shutil.rmtree(self.original_path, ignore_errors=True)
                shutil.move(self.working_path, self.original_path)
