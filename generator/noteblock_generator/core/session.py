from __future__ import annotations

import os
import shutil
import signal
from pathlib import Path

import typer
from click import UsageError

from .cache import BlocksCache
from .utils.console import Console
from .utils.files import backup_files, hash_files
from .world import World


class UserCancelled(Exception): ...


_HANDLED_SIGNALS = set(signal.Signals) - {
    # uncatchable signals
    signal.SIGKILL,
    signal.SIGSTOP,
}


class IgnoreInterrupt:
    def __enter__(self):
        self._original_handlers = {
            sig: signal.signal(sig, signal.SIG_IGN) for sig in _HANDLED_SIGNALS
        }
        return self

    def __exit__(self, exc_type, exc_value, tb):
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)


aborted_message = "Safely aborted. No changes were made."


class WorldGeneratingSession:
    def __init__(self, path: Path, *, use_cache: bool):
        self.original_path = path
        self.working_path: str | None = None
        self.world: World | None = None
        self.world_hash: int | None = None

        if use_cache:
            self.cache = BlocksCache(str(path))
        else:
            self.cache = None
            BlocksCache.delete(str(path))

    def load_world(self):
        if not self.working_path:
            # clone unsuccessful, must generate in-place
            Console.warn(
                "To prevent data corruption, "
                "if you are inside the world,\n{highlighted}.",
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
            os._exit(0)

    def _setup_signal_handlers(self):
        def handle_interrupt(sig, _):
            Console.newline()
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
                "If the game is running, close it and try again.",
            )

    def _cleanup(self, *, commit: bool):
        if not self.working_path:
            return
        try:
            if commit:
                self._commit()
            else:
                Console.success(aborted_message)
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

        self.world.close()

        if self._externally_modified():
            Console.warn(
                "The save files have been modified while generating."
                "\nTo keep this generation, all other changes must be discarded.",
                important=True,
            )
            if not Console.confirm("Confirm to proceed?", default=True):
                Console.success(aborted_message)
                raise typer.Exit()
            Console.success(
                "If you are inside the world, exit and re-enter to see the result.",
            )

        with IgnoreInterrupt():
            # This section is critical but should be very fast (< 0.1s)
            # No need to handle signals, just ignore them
            if self.working_path:
                shutil.rmtree(self.original_path, ignore_errors=True)
                shutil.move(self.working_path, self.original_path)
            if self.cache:
                self.cache.save()
