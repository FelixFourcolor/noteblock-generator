from __future__ import annotations

import math
import re
from collections.abc import Iterator
from functools import cache
from itertools import product
from typing import TYPE_CHECKING, Literal, NamedTuple

from .coordinates import DIRECTION_NAMES, Direction

if TYPE_CHECKING:
    from .api.types import BlockMap, BlockState, BlockType, Size
    from .coordinates import XYZ, DirectionName

    TiltName = Literal["up", "down"]
    AlignName = Literal["left", "center", "right"]


DIRECTION_PATTERN = re.compile("|".join(DIRECTION_NAMES))


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
        theme: list[BlockState],
        blend: bool,
        partial: bool,
    ):
        self.blocks = blocks
        self.origin_x, self.origin_y, self.origin_z = coordinates
        self.facing = Direction[facing]
        self.tilt = tilt
        self.align = align
        self.theme = theme
        self.partial = partial
        self.empty_block = None if blend else "air"

        self.length = size.length
        self.width = size.width
        self.height = size.height
        self.bounds = self._get_bounds()

        # to alternate between rounding up and down in edge cases
        self._theme_should_round_up = True

    def __hash__(self):
        return 1

    def __iter__(self) -> Iterator[tuple[XYZ, BlockState | None]]:
        if self.partial:
            for str_coords, block in self.blocks.items():
                x, y, z = map(int, str_coords.split(" "))
                yield (
                    self.translate_position((x, y, z)),
                    self.translate_block(block, z),
                )
            return

        for x, y, z in product(
            range(self.length), range(self.height), range(self.width)
        ):
            yield (
                self.translate_position((x, y, z)),
                self.translate_block(self.blocks.get(f"{x} {y} {z}"), z),
            )

    def translate_block(self, block: BlockType, z: int) -> BlockState | None:
        if block is None:
            return self.empty_block

        if block == 0:  # magic value for theme block
            block = self.get_theme(z)

        return self.translate_blockstate(block)

    def get_theme(self, z: int) -> BlockState:
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

    @cache
    def translate_blockstate(self, block: BlockState) -> BlockState:
        def translate_direction(match: re.Match) -> str:
            raw_dir = Direction[match.group(0)]
            rotated_dir = Direction(self.facing.rotate(raw_dir))
            return rotated_dir.name

        return DIRECTION_PATTERN.sub(translate_direction, block)

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
