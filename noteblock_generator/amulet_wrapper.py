# Copyright Amulet Team. (https://www.amuletmc.com/)
# https://github.com/Amulet-Team/Amulet-Core/blob/update-licence-info-2/LICENSE

from __future__ import annotations

from typing import Callable, Optional

import amulet

from .generator_utils import Direction, terminal_width
from .main import logger
from .parser import Note

ChunkType = amulet.api.chunk.Chunk
BlockType = amulet.api.Block
WorldType = amulet.api.level.World
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

    def __init__(self, delay: int, direction: Direction):
        # MINECRAFT's BUG: repeater's direction is reversed
        super().__init__("repeater", delay=delay, facing=-direction)


class Redstone(Block):
    """A convenience class for redstone wires"""

    def __init__(self, *connections: Direction):
        # Connected to all sides by default
        if not connections:
            connections = tuple(Direction)
        # Only allow connecting sideways, because that's all we need for this build
        super().__init__(
            "redstone_wire",
            **{Direction(direction).name: "side" for direction in connections},
        )


class World(WorldType):
    """A wrapper of amulet World,
    with modified methods to get/set blocks that optimize performance for our specific usage
    """

    _VERSION = ("java", (1, 20))
    _level: WorldType
    dimension: str

    @classmethod
    def load(cls, *, path: str):
        return cls(path, amulet.load_format(path))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._block_translator_cache = {}
        self._chunk_cache: dict[tuple[int, int], ChunkType] = {}
        self._translator = self.translation_manager.get_version(*self._VERSION).block
        self.all_players = tuple(self.get_player(i) for i in self.all_player_ids())

    def get_block(self, coordinates: tuple[int, int, int], dimension: str):
        """Modified version of get_version_block, optimized for performance"""

        x, y, z = coordinates
        (cx, offset_x), (cz, offset_z) = divmod(x, 16), divmod(z, 16)
        chunk = self.get_chunk(cx, cz, dimension)

        src_blocks = chunk.get_block(offset_x, y, offset_z).block_tuple
        block, _, _ = self._translator.from_universal(src_blocks[0])
        if isinstance(block, BlockType):
            for extra_block in src_blocks[1:]:
                block += extra_block  # no need to translate, we will remove it anyway
        return block

    def set_block(
        self, coordinates: tuple[int, int, int], block: BlockType, dimension: str
    ):
        x, y, z = coordinates
        (cx, offset_x), (cz, offset_z) = divmod(x, 16), divmod(z, 16)
        chunk = self.get_chunk(cx, cz, dimension)
        universal_block = self._translate_block(block)
        chunk.set_block(offset_x, y, offset_z, universal_block)
        if (x, y, z) in chunk.block_entities:
            del chunk.block_entities[x, y, z]
        chunk.changed = True

    def get_chunk(self, cx: int, cz: int, dimension: str):
        try:
            return self._chunk_cache[cx, cz]
        except KeyError:
            try:
                chunk = super().get_chunk(cx, cz, dimension)
            except amulet.api.errors.ChunkLoadError:
                message = f"WARNING - Missing chunk {(cx, cz)}"
                end_of_line = " " * max(0, terminal_width() - len(message))
                logger.warning(f"{message}{end_of_line}")
                chunk = self.create_chunk(cx, cz, dimension)
            self._chunk_cache[cx, cz] = chunk
            return chunk

    def _translate_block(self, block: BlockType, /):
        try:
            return self._block_translator_cache[block]
        except KeyError:
            universal_block, _, _ = self._translator.to_universal(block)
            self._block_translator_cache[block] = universal_block
            return universal_block
