from typing import Literal

from msgspec import Struct

BlockName = str
Properties = dict[str, str | int]


class BlockData(Struct):
    name: BlockName
    properties: Properties


NullableBlockData = BlockData | None


StrCoords = str  # f"{x} {y} {z}"
ThemeBlock = Literal[0]
BlockMap = dict[StrCoords, BlockName | ThemeBlock | BlockData]


class Size(Struct):
    width: int
    height: int
    length: int


class BuildingDTO(Struct):
    size: Size
    blocks: BlockMap
