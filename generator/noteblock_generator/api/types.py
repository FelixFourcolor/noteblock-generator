from typing import Literal

from msgspec import Struct

BlockName = str
BlockProperties = dict[str, str | int]


class Block(Struct):
    name: BlockName
    properties: BlockProperties = {}


StrCoord = str  # f"{x} {y} {z}"
ThemeBlock = Literal[0]
BlockType = BlockName | ThemeBlock | Block | None
BlockMap = dict[StrCoord, BlockType]


class Size(Struct):
    width: int
    height: int
    length: int


class Building(Struct):
    size: Size
    blocks: BlockMap
