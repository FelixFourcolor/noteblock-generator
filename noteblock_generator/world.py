# Copyright Amulet Team. (https://www.amuletmc.com/)
# https://github.com/Amulet-Team/Amulet-Core/blob/update-licence-info-2/LICENSE

from __future__ import annotations

import shutil
from functools import cached_property
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Callable, Optional

import amulet

from . import amulet_fix
from .generator_utils import (
    Direction,
    DirectionType,
    PreventKeyboardInterrupt,
    UserPrompt,
    backup_directory,
    hash_directory,
    progress_bar,
    terminal_width,
)
from .main import logger
from .parser import Note, UserError

ChunkType = amulet.api.chunk.Chunk
BlockType = amulet.api.Block
WorldType = amulet.api.level.World | amulet.api.level.Structure
PlacementType = BlockType | Callable[[tuple[int, int, int]], Optional[BlockType]]


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

    def __init__(self, delay: int, direction: DirectionType):
        # MiNECRAFT's BUG: repeater's direction is reversed
        super().__init__("repeater", delay=delay, facing=(-Direction(direction)).name)


class Redstone(Block):
    """A convenience class for redstone wires"""

    def __init__(self, *connections: DirectionType):
        # only support connecting sideways,
        # because that's all we need for this build
        if connections:
            super().__init__(
                "redstone_wire",
                **{Direction(direction).name: "side" for direction in connections},
            )
        else:
            # connected to all sides by default
            super().__init__(
                "redstone_wire",
                **{direction.name: "side" for direction in Direction},
            )


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
        try:
            # make a copy of World to work on that one
            self._path_backup = backup_directory(self._path)
            # load
            self._level = level = amulet_fix.load_level(str(self._path_backup))
            # keep a hash of the original World
            # to detect if user has entered the world while generating.
            self._hash = hash_directory(self._path)
            # see self.save() for when this is used
        except Exception as e:
            raise UserError(f"Path {self._path} is invalid\n{type(e).__name__}: {e}")

        self._translator = level.translation_manager.get_version(*self._VERSION).block
        self._players = tuple(level.get_player(i) for i in level.all_player_ids())
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._level.close()
        shutil.rmtree(self._path_backup, ignore_errors=True)

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
            wrapper.commit_chunk(chunk, self._dimension)
            # saving takes approximately half the time
            progress_bar(2 * total + (progress + 1), 3 * total, text="Generating")
        self._level.history_manager.mark_saved()
        wrapper.save()

        # Windows fix: must close level before moving its folder
        self._level.close()

    def save(self, *, quiet: bool):
        # Check if World has been modified,
        # if so get user confirmation to discard all changes.
        try:
            modified_by_another_process = (
                self._hash is None or self._hash != hash_directory(self._path)
            )
        except FileNotFoundError:
            modified_by_another_process = False
        if modified_by_another_process:
            logger.warning("Your save files have been modified by another process")
            logger.warning(
                "To keep this generation, all other changes must be discarded"
            )
            UserPrompt.warning(
                "Confirm to proceed? [y/N] ",
                yes=("y", "yes"),
                blocking=True,
            )
        # Move the copy World back to its original location,
        # disable keyboard interrupt to prevent corrupting files
        with PreventKeyboardInterrupt():
            shutil.rmtree(self._path, ignore_errors=True)
            shutil.move(self._path_backup, self._path)
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
                chunk = self._level.get_chunk(cx, cz, self._dimension)
            except amulet.api.errors.ChunkLoadError:
                message = f"Missing chunk {(cx, cz)}"
                end_of_line = " " * max(0, terminal_width() - len(message) - 11)
                logger.warning(f"{message}{end_of_line}")
                chunk = self._level.create_chunk(cx, cz, self._dimension)
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
    def _dimension(self):
        return "minecraft:" + self.dimension

    @property
    def bounds(self):
        return self._level.bounds(self._dimension)

    # -----------------------------------------------------------------------------
    # The methods below are properties so that they are lazily evaluated,
    # so that they are only called if user uses relative location/dimension/orientation,
    # and cached so that loggings are only called once

    @cached_property
    def player_location(self) -> tuple[int, int, int]:
        results = {p.location for p in self._players}
        if not results:
            out = (0, 63, 0)
            logger.warning(f"No players detected. Default location {out} is used.")
            return out
        if len(results) > 1:
            raise UserError(
                "There are more than 1 player in the world. Relative location is not supported."
            )
        out = results.pop()
        out = (round(out[0]), round(out[1]), round(out[2]))
        logger.info(f"Player's location: {out}")
        return out

    @cached_property
    def player_dimension(self) -> str:
        results = {p.dimension for p in self._players}
        if not results:
            out = "overworld"
            logger.warning(f"No players detected. Default dimension {out} is used.")
            return out
        if len(results) > 1:
            raise UserError(
                "There are more than 1 player in the world. Relative dimension is not supported."
            )
        out = results.pop()
        if out.startswith("minecraft:"):
            out = out[10:]
        logger.info(f"Player's dimension: {out}")
        return out

    @cached_property
    def player_orientation(self) -> tuple[int, int]:
        results = {p.rotation for p in self._players}
        if not results:
            out = (0, 45)
            logger.warning(f"No players detected. Default orientation {out} is used.")
            return out
        if len(results) > 1:
            raise UserError(
                "There are more than 1 player in the world. Relative orientation is not supported."
            )
        out = results.pop()
        out = (int(out[0]), int(out[1]))
        logger.info(f"Player's orientation: {out}")
        return out

    def __hash__(self):
        return 0
