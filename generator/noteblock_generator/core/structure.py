from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, NamedTuple

from ..api.types import BlockData, Building, Properties
from .cache import BlocksCache
from .coordinates import DIRECTION_NAMES, Direction

if TYPE_CHECKING:
    from ..api.types import NullableBlockData
    from .coordinates import XYZ, DirectionName, TiltName


air = BlockData("air", {})


class Structure:
    def __init__(
        self,
        *,
        data: Building,
        position: XYZ,
        direction: DirectionName,
        tilt: TiltName,
        theme: str,
        blend: bool,
        cache: BlocksCache | None,
    ):
        size = data.size
        self.length = size.length
        self.height = size.height
        self.width = size.width
        self.volume = self.length * self.height * self.width
        self.blocks = data.blocks
        self.origin_x, self.origin_y, self.origin_z = position
        self.direction = Direction[direction]
        self.tilt = tilt
        self.theme = theme
        self.blend = blend
        self.bounds = self._get_bounds()
        self.cache = cache

    def __iter__(self) -> Iterator[None | tuple[XYZ, NullableBlockData]]:
        for x in range(self.length + 1):
            for y in range(self.height + 1):
                for z in range(self.width + 1):
                    yield self.get_placement((x, y, z))

    def get_placement(self, coords: XYZ) -> None | tuple[XYZ, NullableBlockData]:
        translated_coords = self.translate_position(coords)
        block = self.get_block(coords)

        if self.cache:
            cached_block = self.cache[translated_coords]
            if block == cached_block or block is None and cached_block == air:
                # block == None means blend,
                # if cache is already air, no need to do anything
                return None
            self.cache[translated_coords] = block

        return translated_coords, block

    def get_block(self, coords: XYZ) -> NullableBlockData:
        x, y, z = coords
        block = self.blocks.get(f"{x} {y} {z}", None if self.blend else air)

        if block is None:
            return None

        if isinstance(block, BlockData):
            block.properties = self.translate_properties(block.properties)
            return block

        if block == 0:  # magic value for "use theme block"
            name = self.theme
        else:
            name = block
        return BlockData(name=name, properties={})

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

    def translate_properties(self, data: Properties):
        translated: Properties = {}

        for key, value in data.items():
            if key in DIRECTION_NAMES:
                key = self.translate_direction(key)
            if value in DIRECTION_NAMES:
                value = self.translate_direction(value)
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


class Bounds(NamedTuple):
    min_x: int
    max_x: int
    min_y: int
    max_y: int
    min_z: int
    max_z: int
