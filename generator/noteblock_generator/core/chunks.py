from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ..data.schema import BlockState
    from .coordinates import XYZ, XZ

    ChunkEdits = dict[XYZ, BlockState | None]
    ChunksData = dict[XZ, ChunkEdits]


def organize_chunks(blocks: Iterable[tuple[XYZ, BlockState | None]]):
    chunks: ChunksData = {}

    for (x, y, z), block in blocks:
        cx, offset_x = divmod(x, 16)
        cz, offset_z = divmod(z, 16)
        if (cx, cz) not in chunks:
            chunks[cx, cz] = {}
        chunks[cx, cz][offset_x, y, offset_z] = block
        yield

    return chunks
