"""Transpiled from TypeScript."""

from typing_extensions import Any, Dict, Literal, TypedDict, Union

class Size(TypedDict):
  width: float
  length: float
  height: float

BlockName = str

class BlockData(TypedDict):
  name: str
  properties: Dict[str,Any]

BlockType = Union[str,Literal[0],BlockData]

BlockMap = Dict[str,BlockType]

class BuildingDTO(TypedDict):
  size: Size
  blocks: BlockMap
