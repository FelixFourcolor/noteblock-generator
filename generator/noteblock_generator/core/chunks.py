from __future__ import annotations

from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from ..api.types import Block
    from .coordinates import XYZ, XZ
    from .structure import Structure

    ChunkPlacement = dict[XYZ, Block | None]
    ChunksData = dict[XZ, ChunkPlacement]


@final
class ChunkProcessor:
    def __init__(self, structure: Structure):
        self.structure = structure
        self._chunks: ChunksData = {}
        self._finished = False

    def process(self):
        for placement in self.structure:
            if placement:
                coords, block = placement
                self[coords] = block
            yield

        self._finished = True

    @property
    def count(self) -> int:
        if self._finished:
            return len(self._chunks)

        raise RuntimeError("Cannot access chunks count until processing is complete.")

    def __setitem__(self, coords: XYZ, placement: Block | None):
        x, y, z = coords
        cx, offset_x = divmod(x, 16)
        cz, offset_z = divmod(z, 16)
        if (cx, cz) not in self._chunks:
            self._chunks[cx, cz] = {}
        self._chunks[cx, cz][offset_x, y, offset_z] = placement

    def __iter__(self):
        yield from self._chunks.items()
