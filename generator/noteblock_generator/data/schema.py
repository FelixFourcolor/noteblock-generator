from typing import Literal

from msgspec import Struct

BlockState = str  # "note_block[note=5]"
StrCoord = str  # "{x} {y} {z}"


ThemeBlock = Literal[0]
BlockType = BlockState | ThemeBlock | None
BlockMap = dict[StrCoord, BlockType]


class Size(Struct, frozen=True):
    width: int
    height: int
    length: int


class Building(Struct):
    blocks: BlockMap
    size: Size


class Payload(Struct):
    blocks: BlockMap | None = None
    size: Size | None = None
    error: str | None = None
