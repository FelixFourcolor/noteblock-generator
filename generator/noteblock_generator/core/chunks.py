from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .coordinates import XYZ, XZ
    from .structure import BlockType, Structure

    ChunkPlacement = dict[XYZ, BlockType]
    ChunksData = dict[XZ, ChunkPlacement]


class ChunkProcessor:
    def __init__(self, structure: Structure):
        self.structure = structure

        self._chunks: ChunksData = {}
        bounds = structure.bounds
        min_cx = bounds.min_x // 16
        min_cz = bounds.min_z // 16
        max_cx = bounds.max_x // 16
        max_cz = bounds.max_z // 16
        for cx in range(min_cx, max_cx + 1):
            for cz in range(min_cz, max_cz + 1):
                self._chunks[cx, cz] = {}

        self.chunks_count = len(self._chunks)
        self._blocks_per_chunk = structure.volume // self.chunks_count

    def process(self):
        for i, (coords, placement) in enumerate(self.structure):
            self[coords] = placement
            if i % self._blocks_per_chunk == 0:
                yield

    def __setitem__(self, coords: XYZ, placement: BlockType):
        x, y, z = coords
        cx, offset_x = divmod(x, 16)
        cz, offset_z = divmod(z, 16)
        self._chunks[cx, cz][offset_x, y, offset_z] = placement

    def __iter__(self):
        return iter(self._chunks.items())
