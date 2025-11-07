from typing import Literal

from msgspec import Struct

BlockName = str  # "note_block[note=5]"
StrCoord = str  # f"{x} {y} {z}"


ThemeBlock = Literal[0]
BlockType = BlockName | ThemeBlock | None
BlockMap = dict[StrCoord, BlockType]


class Size(Struct):
    width: int
    height: int
    length: int


class Building(Struct):
    size: Size
    blocks: BlockMap
