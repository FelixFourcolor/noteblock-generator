from __future__ import annotations

import os
import shutil
from pathlib import Path
from signal import SIG_IGN, SIGINT, signal

import typer
from click import UsageError

from .utils.console import Console
from .utils.files import backup_files, hash_files
from .world import World


class UserCancelled(Exception): ...


class PreventKeyboardInterrupt:
    def __enter__(self):
        self.handler = signal(SIGINT, SIG_IGN)

    def __exit__(self, exc_type, exc_value, tb):
        signal(SIGINT, self.handler)


aborted_message = "Aborted. No changes were made."


class WorldGeneratingSession:
    def __init__(self, path: Path):
        self.original_path = path
        self.working_path: str | None = None
        self.world: World | None = None
        self.world_hash: int | None = None

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
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._cleanup(commit=exc_type is None)

        if exc_type is KeyboardInterrupt:
            # Ctrl+C doesn't create a new line
            Console.success(f"\n{aborted_message}")
            self._cleanup(commit=False)
            os._exit(130)  # a hack to terminate NonBlockingPrompt's thread

        if exc_type is UserCancelled:
            Console.success(aborted_message)
            return True

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

        if commit:
            self._commit()
        shutil.rmtree(self.working_path, ignore_errors=True)

    def _detect_external_modifications(self) -> bool:
        try:
            return self.world_hash is None or self.world_hash != self._compute_hash()
        except FileNotFoundError:
            return True

    def _commit(self):
        modified = self._detect_external_modifications()

        if modified:
            Console.warn(
                "The save files have been modified while generating."
                "\nTo keep this generation, all other changes must be discarded.",
                important=True,
            )
            if not Console.confirm("Confirm to proceed?", default=True):
                Console.success(aborted_message)
                raise typer.Exit()

        with PreventKeyboardInterrupt():
            if not self.world:
                return
            self.world.close()
            if self.working_path:
                shutil.rmtree(self.original_path, ignore_errors=True)
                shutil.move(self.working_path, self.original_path)

        if modified:
            Console.success(
                "If you are inside the world, exit and re-enter to see the result.",
                important=True,
            )
