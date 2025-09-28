from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, NamedTuple

from .coordinates import DIRECTION_NAMES, Direction

if TYPE_CHECKING:
    from ..api.types import BlockData, BuildingDTO
    from .coordinates import XYZ, DirectionName, TiltName

    BlockType = BlockData | None


class Bounds(NamedTuple):
    min_x: int
    max_x: int
    min_y: int
    max_y: int
    min_z: int
    max_z: int


class Structure:
    def __init__(
        self,
        *,
        data: BuildingDTO,
        position: XYZ,
        direction: DirectionName,
        tilt: TiltName,
        theme: str,
        blend: bool,
    ):
        size = data["size"]
        self.length = int(size["length"])
        self.height = int(size["height"])
        self.width = int(size["width"])
        self.volume = self.length * self.height * self.width
        self.blocks = data["blocks"]
        self.origin_x, self.origin_y, self.origin_z = position
        self.direction = Direction[direction]
        self.tilt = tilt
        self.theme = theme
        air: BlockData = {"name": "air", "properties": {}}
        self.space_block = None if blend else air
        self.bounds = self._get_bounds()

    def __iter__(self) -> Iterator[tuple[XYZ, BlockType]]:
        for x in range(self.length + 1):
            for y in range(self.height + 1):
                for z in range(self.width + 1):
                    coords = (x, y, z)
                    yield self.translate_position(coords), self.get_block(coords)

    def get_block(self, coords: XYZ) -> BlockType:
        x, y, z = coords

        key = f"{x} {y} {z}"
        if key not in self.blocks:
            return self.space_block

        block = self.blocks[key]

        if isinstance(block, dict):
            block["properties"] = self.translate_properties(block["properties"])
            return block

        block_name = block or self.theme
        return {"name": block_name, "properties": {}}

    def translate_position(self, coords: XYZ):
        raw_x, raw_y, raw_z = coords

        rotated_x, rotated_z = self.direction.rotate((
            raw_x,
            raw_z - self.width // 2,
        ))

        translated_x = self.origin_x + rotated_x
        translated_y = self.origin_y + raw_y
        translated_z = self.origin_z + rotated_z

        if self.tilt == "down":
            translated_y -= self.height - 2

        return translated_x, translated_y, translated_z

    def translate_direction(self, name: DirectionName):
        raw_dir = Direction[name]
        rotated_dir = Direction(self.direction.rotate(raw_dir))
        return rotated_dir.name

    def translate_properties(self, data: dict[str, Any]):
        translated: dict[str, Any] = {}

        for key, value in data.items():
            if key in DIRECTION_NAMES:
                key = self.translate_direction(key)

            if value in DIRECTION_NAMES:
                value = self.translate_direction(value)
            elif isinstance(value, dict):
                value = self.translate_properties(value)

            translated[key] = value

        return translated

    def _get_bounds(self) -> Bounds:
        start_x, start_y, start_z = self.translate_position((0, 0, 0))
        end_x, end_y, end_z = self.translate_position((
            self.length - 1,
            self.height - 1,
            self.width - 1,
        ))
        return Bounds(
            min_x=min(start_x, end_x),
            max_x=max(start_x, end_x),
            min_y=start_y,
            max_y=end_y,
            min_z=min(start_z, end_z),
            max_z=max(start_z, end_z),
        )
