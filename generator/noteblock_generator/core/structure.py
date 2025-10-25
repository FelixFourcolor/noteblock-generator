from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, NamedTuple, final

from ..api.types import Block, BlockName, BlockProperties, BlockType, Building
from .blend import DANGER_LIST
from .cache import Cache
from .coordinates import DIRECTION_NAMES, Direction
from .utils.console import Console

if TYPE_CHECKING:
    from ..api.types import Block
    from .coordinates import XYZ, DirectionName, TiltName


@final
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
        walkable: bool,
        cache: Cache | None,
    ):
        self.blocks = data.blocks
        self.origin_x, self.origin_y, self.origin_z = position
        self.direction = Direction[direction]
        self.tilt = tilt
        self.theme = theme
        self.blend = blend
        self.walkable = walkable
        self.cache = cache

        size = data.size
        self.length = size.length
        self.width = size.width
        self.height = size.height
        if walkable:
            self.height += 1  # to fit player's height
        self.volume = self.length * self.height * self.width
        self.bounds = self._get_bounds()

        if blend:
            Console.warn(
                "Blend mode is experimental. Turn it off if you encounter issues."
            )

    def __iter__(self) -> Iterator[None | tuple[XYZ, Block | None]]:
        for x in range(self.length):
            for y in range(self.height):
                for z in range(self.width):
                    yield self.get_placement((x, y, z))

    def get_placement(self, coords: XYZ) -> None | tuple[XYZ, Block | None]:
        translated_coords = self.translate_position(coords)
        block = self.get_block(coords)

        if self.cache:
            cached_block = self.cache[translated_coords]
            if block == cached_block:
                return None
            if block is None and isinstance(cached_block, str):
                if cached_block not in DANGER_LIST:
                    return None
            self.cache[translated_coords] = block

        if isinstance(block, str):
            block = Block(block)
        return translated_coords, block

    def get_block(self, coords: XYZ) -> BlockName | Block | None:
        x, y, z = coords
        block: BlockType | None = self.blocks.get(
            f"{x} {y} {z}", self._get_implied_block((x, y, z))
        )

        if block is None:
            return None

        if isinstance(block, Block):
            block.properties = self.translate_properties(block.properties)
            return block

        if block == 0:
            return self.theme

        return block

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
            translated_y -= self.height - 1
            if self.walkable:
                translated_y += 1

        return translated_x, translated_y, translated_z

    def translate_direction(self, name: DirectionName):
        raw_dir = Direction[name]
        rotated_dir = Direction(self.direction.rotate(raw_dir))
        return rotated_dir.name

    def translate_properties(self, data: BlockProperties):
        translated: BlockProperties = {}

        for key, value in data.items():
            if key in DIRECTION_NAMES:
                key = self.translate_direction(key)
            if value in DIRECTION_NAMES:
                value = self.translate_direction(value)
            translated[key] = value

        return translated

    def _get_implied_block(self, coords: XYZ) -> BlockName | None:
        x, y, z = coords

        if self.walkable and z == self.width // 2 and x in range(self.length - 1):
            if y in [self.height - 1, self.height - 2]:
                return "air"
            if y == self.height - 3:
                return "glass"

        if not self.blend:
            return "air"

        if x in (0, self.length - 1) or z in (0, self.width - 1):
            return "air"

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
