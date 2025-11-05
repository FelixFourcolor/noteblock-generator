from __future__ import annotations

import math
from collections.abc import Iterator
from typing import TYPE_CHECKING, Literal, NamedTuple, final

from .api.types import Block, BlockProperties
from .coordinates import DIRECTION_NAMES, Direction

if TYPE_CHECKING:
    from .api.types import BlockMap, BlockName, BlockType, Size
    from .coordinates import XYZ, DirectionName

    TiltName = Literal["up", "down"]
    AlignName = Literal["left", "center", "right"]


@final
class Structure:
    def __init__(
        self,
        *,
        size: Size,
        blocks: BlockMap,
        coordinates: XYZ,
        facing: DirectionName,
        tilt: TiltName,
        align: AlignName,
        theme: list[BlockName],
        blend: bool,
        partial: bool,
    ):
        self.blocks = blocks
        self.origin_x, self.origin_y, self.origin_z = coordinates
        self.facing = Direction[facing]
        self.tilt = tilt
        self.align = align
        self.theme = theme
        self.blend = blend
        self.partial = partial

        self.length = size.length
        self.width = size.width
        self.height = size.height
        self.blocks_count = (
            len(blocks) if partial else self.length * self.height * self.width
        )
        self.bounds = self._get_bounds()

        # to alternate between rounding up and down in edge cases
        self._theme_should_round_up = True

    def __iter__(self) -> Iterator[None | tuple[XYZ, Block | None]]:
        if self.partial:
            for str_coords, block in self.blocks.items():
                x, y, z = map(int, str_coords.split(" "))
                yield self.translate_position((x, y, z)), self.translate_block(block, z)
            return

        for x in range(self.length):
            for y in range(self.height):
                for z in range(self.width):
                    str_coords = f"{x} {y} {z}"
                    yield (
                        self.translate_position((x, y, z)),
                        self.translate_block(
                            self.blocks.get(str_coords, None if self.blend else "air"),
                            z,
                        ),
                    )

    def translate_block(self, block: BlockType, z: int) -> Block | None:
        if block is None:
            return None

        if isinstance(block, Block):
            # apply rotation to directional properties (e.g. "west"), if any
            properties = self.translate_properties(block.properties)
            return Block(block.name, properties)

        if block == 0:  # magic value for theme block
            return Block(self.get_theme(z))

        return Block(block)

    def get_theme(self, z: int) -> BlockName:
        max_z = self.width - 1
        if z == 0:
            return self.theme[0]
        if z == max_z:
            return self.theme[-1]

        themes_count = len(self.theme)
        theme_index = (z * themes_count) / max_z

        if int(theme_index) != theme_index:
            return self.theme[int(theme_index)]

        # Edge case: when the index is a whole number
        if self._theme_should_round_up:
            self._theme_should_round_up = False
            theme_index = int(theme_index)
        else:
            self._theme_should_round_up = True
            theme_index = int(theme_index) - 1
        return self.theme[theme_index]

    def translate_position(self, coords: XYZ):
        raw_x, raw_y, raw_z = coords

        if self.align == "center":
            shifted_z = raw_z - math.floor((self.width - 1) / 2)
        elif self.align == "left":
            shifted_z = raw_z - self.width + 1
        else:  # right
            shifted_z = raw_z

        rotated_x, rotated_z = self.facing.rotate((raw_x, shifted_z))

        translated_x = self.origin_x + rotated_x
        translated_y = self.origin_y + raw_y
        translated_z = self.origin_z + rotated_z

        if self.tilt == "down":
            translated_y -= self.height - 2

        return translated_x, translated_y, translated_z

    def translate_direction(self, name: DirectionName):
        raw_dir = Direction[name]
        rotated_dir = Direction(self.facing.rotate(raw_dir))
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
