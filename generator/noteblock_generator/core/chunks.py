from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..api.types import BlockData
    from .coordinates import XYZ, XZ
    from .structure import Structure

    ChunkPlacement = dict[XYZ, BlockData | None]
    ChunksData = dict[XZ, ChunkPlacement]


class ChunkProcessor:
    def __init__(self, structure: Structure):
        self.structure = structure
        self._chunks: ChunksData = {}
        self._chunks_count_ready = False

    def process(self):
        for placement in self.structure:
            if placement:
                coords, block = placement
                self[coords] = block
            yield

        self._chunks_count_ready = True

    @property
    def chunks_count(self) -> int:
        if self._chunks_count_ready:
            return len(self._chunks)
        raise RuntimeError("Cannot access chunks count until processing is complete.")

    def __setitem__(self, coords: XYZ, placement: BlockData | None):
        x, y, z = coords
        cx, offset_x = divmod(x, 16)
        cz, offset_z = divmod(z, 16)
        if (cx, cz) not in self._chunks:
            self._chunks[cx, cz] = {}
        self._chunks[cx, cz][offset_x, y, offset_z] = placement

    def __iter__(self):
        return iter(self._chunks.items())
