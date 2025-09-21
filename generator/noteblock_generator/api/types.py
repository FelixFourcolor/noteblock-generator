"""Transpiled from TypeScript."""

from typing_extensions import Any, Dict, TypedDict, Union

class Size(TypedDict):
  width: float
  length: float
  height: float

BlockName = str

class BlockData(TypedDict):
  name: str
  properties: Dict[str,Any]

BlockType = Union[None,str,BlockData]

BlockMap = Dict[str,BlockType]

class BuildingDTO(TypedDict):
  size: Size
  blocks: BlockMap
