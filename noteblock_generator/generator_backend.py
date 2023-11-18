from __future__ import annotations

from typing import TYPE_CHECKING

import amulet

from .generator_utils import Direction

if TYPE_CHECKING:
    from collections.abc import Iterable

ChunkType = amulet.api.chunk.Chunk
BlockType = amulet.api.Block
WorldType = amulet.api.level.World


class _BlockMeta(type):
    def __call__(self, generator: World, /, *args, **kwargs):
        return generator.translate_block(super().__call__(*args, **kwargs))


class Block(BlockType, metaclass=_BlockMeta):
    def __init__(self, name: str, **properties):
        properties = {k: amulet.StringTag(v) for k, v in properties.items()}
        super().__init__("minecraft", name, properties)


class NoteBlock(Block):
    def __init__(self, note: int, instrument: str):
        super().__init__("note_block", note=note, instrument=instrument)


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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._block_translator = self.translation_manager.get_version(
            "java", (1, 20)
        ).block

    def save(self, chunks: Iterable[ChunkType], dimension: str):
        wrapper = self.level_wrapper
        for progress, chunk in enumerate(chunks):
            wrapper.commit_chunk(chunk, dimension)
            yield progress
        self.history_manager.mark_saved()
        wrapper.save()

    def translate_block(self, block: BlockType, /) -> BlockType:
        return self._block_translator.to_universal(block)[0]
