from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .api.types import BlockName
    from .coordinates import XYZ, XZ
    from .structure import Structure

    ChunkPlacement = dict[XYZ, BlockName | None]
    ChunksData = dict[XZ, ChunkPlacement]


class ChunksManager:
    def __init__(self):
        self._chunks: ChunksData = {}
        self._process_finished = False

    def process(self, structure: Structure):
        for (x, y, z), block in structure:
            cx, offset_x = divmod(x, 16)
            cz, offset_z = divmod(z, 16)
            if (cx, cz) not in self._chunks:
                self._chunks[cx, cz] = {}
            self._chunks[cx, cz][offset_x, y, offset_z] = block
            yield

        self._process_finished = True

    @property
    def count(self) -> int:
        if self._process_finished:
            return len(self._chunks)

        raise RuntimeError("Cannot access chunks count until processing is complete.")

    def __iter__(self):
        yield from self._chunks.items()
