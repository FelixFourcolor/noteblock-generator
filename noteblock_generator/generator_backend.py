from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

import amulet
from amulet.level.formats.anvil_world.format import AnvilFormat

from .generator_utils import Direction
from .parser import Note

if TYPE_CHECKING:
    from generator import Generator

ChunkType = amulet.api.chunk.Chunk
BlockType = amulet.api.Block
WorldType = amulet.api.level.World


class _BlockMeta(type):
    @cache
    def __call__(self, generator: Generator, /, *args, **kwargs):
        return generator.translate_block(super().__call__(*args, **kwargs))


class Block(BlockType, metaclass=_BlockMeta):
    def __init__(self, name: str, **properties):
        properties = {k: amulet.StringTag(v) for k, v in properties.items()}
        super().__init__("minecraft", name, properties)


class NoteBlock(Block):
    def __init__(self, _note: Note):
        super().__init__("note_block", note=_note.note, instrument=_note.instrument)


class Repeater(Block):
    def __init__(self, delay: int, direction: Direction):
        # MINECRAFT's BUG: repeater's direction is reversed
        super().__init__("repeater", delay=delay, facing=-direction)


class Redstone(Block):
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
    @classmethod
    def load(cls, path: str):
        return cls(path, AnvilFormat(path))
