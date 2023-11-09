# Required Notice: Copyright Amulet Team. (https://www.amuletmc.com/)
# https://github.com/Amulet-Team/Amulet-Core/blob/update-licence-info-2/LICENSE

from __future__ import annotations

import _thread
import hashlib
import logging
import os
import shutil
import signal
from enum import Enum
from functools import cached_property
from io import StringIO
from multiprocessing.pool import ThreadPool
from pathlib import Path
from threading import Thread
from typing import Callable, Iterable, Optional, TypeVar

import amulet
from platformdirs import user_cache_dir

from . import amulet_fix
from .main import logger
from .parser import Note, UserError

ChunkType = amulet.api.chunk.Chunk
BlockType = amulet.api.Block
WorldType = amulet.api.level.World | amulet.api.level.Structure
PlacementType = BlockType | Callable[[tuple[int, int, int]], Optional[BlockType]]


class Direction(tuple[int, int], Enum):
    """Minecraft's cardinal direction"""

    # coordinates in (x, z)
    north = (0, -1)
    south = (0, 1)
    east = (1, 0)
    west = (-1, 0)

    def __str__(self):
        return self.name

    # Operator overloading
    # -----------------------------------------------------------------------------
    # Multiplication
    # with another Direction: like complex multiplication, return a Direction
    # with a tuple: like complex multiplication, return a tuple
    # with an int: multiply our non-zero component with the int, return an int

    def __mul__(self, other: _DirectionType) -> _DirectionType:
        if isinstance(other, Direction):
            return Direction(
                (
                    self[0] * other[1] + self[1] * other[0],
                    self[1] * other[1] - self[0] * other[0],
                )
            )
        if isinstance(other, tuple):
            return (
                self[0] * other[1] + self[1] * other[0],
                self[1] * other[1] - self[0] * other[0],
            )
        if isinstance(other, int):
            return max(self, key=abs) * other
        return NotImplemented

    def __rmul__(self, other: _DirectionType) -> _DirectionType:
        return self * other

    def __neg__(self):
        # negation is like multiplying with 0i - 1, which is north
        return self * Direction.north

    # -----------------------------------------------------------------------------
    # Addition and subtraction
    # with a tuple: like complex addition and subtraction, return a tuple
    # with an int: add/subtract our non-zero component with the int, return an int

    def __add__(self, other: _NumType) -> _NumType:
        if isinstance(other, tuple):
            return (self[0] + other[0], self[1] + other[1])
        if isinstance(other, int):
            return max(self, key=abs) + other
        return NotImplemented

    def __radd__(self, other: _NumType) -> _NumType:
        return self + other

    def __sub__(self, other: _NumType) -> _NumType:
        if isinstance(other, tuple):
            return (self[0] - other[0], self[1] - other[1])
        if isinstance(other, int):
            return max(self, key=abs) - other
        return NotImplemented

    def __rsub__(self, other: _NumType) -> _NumType:
        return -self + other

    # -----------------------------------------------------------------------------
    # bool: whether the non-zero component is positive

    def __bool__(self):
        return max(self, key=abs) > 0


_DirectionType = TypeVar("_DirectionType", Direction, tuple[int, int], int)
_NumType = TypeVar("_NumType", tuple[int, int], int)


class Block(BlockType):
    """A thin wrapper of amulet Block, with a more convenient constructor"""

    def __init__(self, name: str, **properties):
        properties = {k: amulet.StringTag(v) for k, v in properties.items()}
        super().__init__("minecraft", name, properties)


class NoteBlock(Block):
    """A covenience class for noteblocks"""

    def __init__(self, _note: Note):
        super().__init__("note_block", note=_note.note, instrument=_note.instrument)


class Repeater(Block):
    """A convenience class for repeaters"""

    def __init__(self, delay: int, direction: Direction):
        # MiNECRAFT's BUG: repeater's direction is reversed
        super().__init__("repeater", delay=delay, facing=(-direction).name)


class Redstone(Block):
    """A convenience class for redstone wires"""

    def __init__(self, *connections: Direction):
        # only support connecting sideways,
        # because that's all we need for this build
        if not connections:
            # connected to all sides by default
            connections = tuple(Direction)
        super().__init__(
            "redstone_wire",
            **{direction.name: "side" for direction in connections},
        )


TERMINAL_WIDTH = min(80, os.get_terminal_size()[0])


def progress_bar(iteration: float, total: float, *, text: str):
    ratio = iteration / total
    percentage = f" {100*ratio:.0f}% "

    alignment_spacing = " " * (6 - len(percentage))
    total_length = max(0, TERMINAL_WIDTH - len(text) - 16)
    fill_length = int(total_length * ratio)
    finished_portion = "#" * fill_length
    remaining_portion = "-" * (total_length - fill_length)
    progress_bar = f"[{finished_portion}{remaining_portion}]" if total_length else ""
    end_of_line = "" if ratio == 1 else "\033[F"

    logger.info(f"{text}{alignment_spacing}{percentage}{progress_bar}{end_of_line}")


class UserPrompt:
    def __init__(self, prompt: str, choices: Iterable[str], *, blocking: bool):
        self._prompt = prompt
        self._choices = choices
        self._thread = Thread(target=self._run, daemon=True)
        if blocking:
            self._thread.run()
        else:
            self._thread.start()

    def _run(self):
        # capture logs to not interrupt the user prompt
        logging.basicConfig(
            format="%(levelname)s - %(message)s",
            stream=(buffer := StringIO()),
            force=True,
        )
        # prompt
        result = input(self._prompt).lower() in self._choices
        # stop capturing
        logging.basicConfig(format="%(levelname)s - %(message)s", force=True)

        if result:
            # release captured logs
            print(f"\n{buffer.getvalue()}", end="")
        else:
            _thread.interrupt_main()

    def wait(self):
        self._thread.join()


def hash_directory(directory: str | Path):
    def update(directory: str | Path, _hash: hashlib._Hash) -> hashlib._Hash:
        for path in sorted(Path(directory).iterdir(), key=lambda p: str(p)):
            _hash.update(path.name.encode())
            if path.is_file():
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        _hash.update(chunk)
            elif path.is_dir():
                _hash = update(path, _hash)
        return _hash

    return update(directory, hashlib.blake2b()).digest()


def copytree(src: Path, dst: Path, *args, **kwargs) -> Path:
    """shutil.copytree,
    but replace dst with dst (1), dst (2), etc. if dst already exists
    """

    _dir, _name = dst.parent, dst.stem
    i = 0
    while True:
        try:
            shutil.copytree(src, dst, *args, **kwargs)
        except FileExistsError:
            if _name.endswith(suffix := f" ({i})"):
                _name = _name[: -len(suffix)]
            _name += f" ({(i := i + 1)})"
            dst = _dir / _name
        else:
            return dst


class PreventKeyboardInterrupt:
    def __enter__(self):
        self.handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

    def __exit__(self, exc_type, exc_value, tb):
        signal.signal(signal.SIGINT, self.handler)


class World:
    """A wrapper of amulet Level,
    with modified methods to get/set blocks that optimize performance for our specific usage
    """

    _VERSION = ("java", (1, 20))
    _level: WorldType
    dimension: str

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._block_translator_cache = {}
        self._chunk_cache: dict[tuple[int, int], ChunkType] = {}
        self._modifications: dict[
            tuple[int, int],  # chunk location
            dict[
                tuple[int, int, int],  # location within chunk
                PlacementType,  # what to do at that location
            ],
        ] = {}

    def __enter__(self):
        cache_dir = Path(user_cache_dir("noteblock-generator"))

        try:
            # make a copy of World to work on that one
            self._path_copy = copytree(self._path, cache_dir / self._path.stem)
            # load
            self._level = level = amulet_fix.load_level(str(self._path_copy))
            self._level.players
            # keep a hash of the original World
            # to detect if user has entered the world while generating.
            self._hash = hash_directory(self._path)
            # see self._save() for when this is used
        except Exception as e:
            if isinstance(e, UserError):
                raise e
            raise UserError(f"Path {self._path} is invalid\n{type(e).__name__}: {e}")

        self._translator = level.translation_manager.get_version(*self._VERSION).block
        self._players = tuple(level.get_player(i) for i in level.all_player_ids())
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._level.close()
        shutil.rmtree(self._path_copy, ignore_errors=True)

    def __getitem__(self, coordinates: tuple[int, int, int]):
        # A modified version of self._level.get_version_block,
        # optimized for performance

        x, y, z = coordinates
        (cx, offset_x), (cz, offset_z) = divmod(x, 16), divmod(z, 16)
        chunk = self._get_chunk(cx, cz)

        src_blocks = chunk.get_block(offset_x, y, offset_z).block_tuple
        block, _, _ = self._translator.from_universal(src_blocks[0])
        if isinstance(block, BlockType):
            for extra_block in src_blocks[1:]:
                block += extra_block  # no need to translate, we will remove it anyway
        return block

    def __setitem__(self, coordinates: tuple[int, int, int], block: PlacementType):
        """Does not actually set blocks,
        but saves what blocks to be set and where into a hashmap organized by chunks
        """

        x, y, z = coordinates
        cx, cz = x // 16, z // 16
        if (cx, cz) not in self._modifications:
            self._modifications[cx, cz] = {}
        self._modifications[cx, cz][x, y, z] = block

    def apply_modifications(self):
        """Actual block-setting happens here"""

        if not self._modifications:
            return

        def _modify_chunk(modifications: dict[tuple[int, int, int], PlacementType]):
            for coordinates, placement in modifications.items():
                if callable(placement):
                    if (block := placement(coordinates)) is not None:
                        self._set_block(*coordinates, block)
                else:
                    self._set_block(*coordinates, placement)

        # Modifications are organize into chunks to optimize multithreading:
        # every thread has to load exactly one chunk
        total = len(self._modifications)
        with ThreadPool() as pool:
            for progress, _ in enumerate(
                pool.imap_unordered(_modify_chunk, self._modifications.values())
            ):
                # so that block-setting and saving uses the same progress bar
                progress_bar(2 * (progress + 1), 3 * total, text="Generating")

        # A modified version of self._level.save,
        # optimized for performance,
        # with customized progress handling so that block-setting and saving uses the same progress bar
        chunks = self._modifications.keys()
        wrapper = self._level.level_wrapper
        for progress, (cx, cz) in enumerate(chunks):
            chunk = self._chunk_cache[cx, cz]
            wrapper.commit_chunk(chunk, self.dimension)
            # saving takes approximately half the time
            progress_bar(2 * total + (progress + 1), 3 * total, text="Generating")
        self._level.history_manager.mark_saved()
        wrapper.save()

    def save(self):
        # Check if World has been modified,
        # if so get user confirmation to discard all changes.
        modified_by_another_process = False
        try:
            _hash = hash_directory(self._path)
        except FileNotFoundError:
            pass
        else:
            if modified_by_another_process := self._hash != _hash:
                UserPrompt(
                    "\nWhile the generator was running, your save files were modified by another process."
                    "\nIf you want to proceed with this program, all other changes must be discarded."
                    "\nConfirm to proceed? [y/N]: ",
                    choices=("y", "yes"),
                    blocking=True,
                )
        # Move the copy World back to its original location,
        # disable keyboard interrupt to prevent corrupting files
        with PreventKeyboardInterrupt():
            shutil.rmtree(self._path, ignore_errors=True)
            shutil.move(self._path_copy, self._path)
        return modified_by_another_process

    def _set_block(self, x: int, y: int, z: int, block: BlockType):
        # A modified version of self._level.set_version_block,
        # optimized for performance

        (cx, offset_x), (cz, offset_z) = divmod(x, 16), divmod(z, 16)
        chunk = self._get_chunk(cx, cz)
        universal_block = self._translate_block(block)
        chunk.set_block(offset_x, y, offset_z, universal_block)
        if (x, y, z) in chunk.block_entities:
            del chunk.block_entities[x, y, z]

    def _get_chunk(self, cx: int, cz: int):
        try:
            return self._chunk_cache[cx, cz]
        except KeyError:
            try:
                chunk = self._level.get_chunk(cx, cz, self.dimension)
            except amulet.api.errors.ChunkLoadError:
                message = f"Error loading chunk {(cx, cz)}"
                end_of_line = " " * max(0, TERMINAL_WIDTH - len(message) - 10)
                logger.warning(f"{message}{end_of_line}")
                chunk = self._level.create_chunk(cx, cz, self.dimension)
            self._chunk_cache[cx, cz] = chunk
            return chunk

    def _translate_block(self, block: BlockType, /):
        try:
            return self._block_translator_cache[block]
        except KeyError:
            universal_block, _, _ = self._translator.to_universal(block)
            self._block_translator_cache[block] = universal_block
            return universal_block

    @property
    def bounds(self):
        return self._level.bounds(self.dimension)

    @property
    def dimensions(self):
        return self._level.dimensions

    # -----------------------------------------------------------------------------
    # The methods below are properties so that they are lazily evaluated,
    # so that they are only called if user uses relative location/dimension/orientation,

    # this one is cached because it's called thrice, once for each coordinate
    @cached_property
    def player_location(self) -> tuple[float, float, float]:
        results = {p.location for p in self._players}
        if not results:
            out = (0, 63, 0)
            logger.warning(f"No players detected. Default location {out} is used.")
            return out
        if len(results) > 1:
            raise UserError(
                "There are more than 1 player in the world. Relative location is not supported."
            )
        return results.pop()

    @property
    def player_dimension(self) -> str:
        results = {p.dimension for p in self._players}
        if not results:
            out = "minecraft:overworld"
            logger.warning(f"No players detected. Default dimension {out} is used.")
            return out
        if len(results) > 1:
            raise UserError(
                "There are more than 1 player in the world. Relative dimension is not supported."
            )
        return results.pop()

    @property
    def player_orientation(self) -> tuple[float, float]:
        results = {p.rotation for p in self._players}
        if not results:
            out = (0.0, 45.0)
            logger.warning(f"No players detected. Default orientation {out} is used.")
            return out
        if len(results) > 1:
            raise UserError(
                "There are more than 1 player in the world. Relative orientation is not supported."
            )
        return results.pop()
