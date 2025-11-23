from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..data.schema import BlockState
    from .coordinates import XYZ, XZ
    from .structure import Structure

    ChunkEdits = dict[XYZ, BlockState | None]
    ChunksData = dict[XZ, ChunkEdits]


class ChunksManager:
    def __init__(self):
        self._chunks: ChunksData = {}

    def process(self, structure: Structure):
        for (x, y, z), block in structure:
            cx, offset_x = divmod(x, 16)
            cz, offset_z = divmod(z, 16)
            if (cx, cz) not in self._chunks:
                self._chunks[cx, cz] = {}
            self._chunks[cx, cz][offset_x, y, offset_z] = block
            yield

    @property
    def count(self) -> int:
        return len(self._chunks)

    def __iter__(self):
        yield from self._chunks.items()
