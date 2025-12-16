from __future__ import annotations

import math
import re
from functools import cache
from itertools import chain, product
from typing import TYPE_CHECKING

from ..cli.args import Align, Tilt, Walkable
from .direction import Direction
from .placement import Placement

if TYPE_CHECKING:
    from re import Match

    from ..data.schema import BlockMap, BlockState, BlockType, Size, ThemeBlock
    from .coordinates import XYZ


DIRECTION_PATTERN = re.compile("|".join(Direction.__members__))
THEME_BLOCK: ThemeBlock = 0


class BlockMapper(Placement):
    def update_size(self, size: Size):
        super().update_size(size)
        # to alternate rounding in boundary cases
        self._theme_should_round_up = True

    def calculate_expansion(self, prev_size: Size) -> BlockMap:
        if prev_size == self.size:
            return {}

        prev_length = prev_size.length
        prev_height = prev_size.height
        prev_width = prev_size.width

        x_expansion = range(prev_length, self.length)
        match self.tilt:
            case Tilt.down:
                y_expansion = range(self.height - prev_height)
            case Tilt.up:
                y_expansion = range(prev_height, self.height)
        match self.align:
            case Align.center:
                offset = math.floor((self.width - prev_width) // 2)
                z_expansion = chain(
                    range(offset), range(prev_width + offset, self.width)
                )
            case Align.left:
                z_expansion = range(self.width - prev_width)
            case Align.right:
                z_expansion = range(prev_width, self.width)

        return {
            f"{x} {y} {z}": None
            for (x, y, z) in chain(
                product(x_expansion, range(self.height), range(self.width)),
                product(range(self.length), y_expansion, range(self.width)),
                product(range(self.length), range(self.height), z_expansion),
            )
        }

    def resolve(self, block: BlockType, coords: XYZ) -> BlockState | None:
        if block is None:
            return self._resolve_space_block(coords)

        if block == THEME_BLOCK:
            block = self._get_theme(coords[2])

        return self._apply_rotation(block)

    def _resolve_space_block(self, coords: XYZ) -> BlockState | None:
        x, y, z = coords

        if self._is_padding(x, z):
            return "air"

        if y < self.height - 3:
            return self.empty_block

        walk_block = "glass" if y == self.height - 3 else "air"
        match self.walkable:
            case Walkable.full:
                return walk_block
            case Walkable.partial:
                return walk_block if self._is_center(z) else self.empty_block
            case Walkable.no:
                return self.empty_block

    def _is_padding(self, x: int, z: int):
        if x == 0:
            return not self._is_center(z)
        return x == self.length - 1 or z in (0, self.width - 1)

    def _is_center(self, z: int):
        if (self.width % 2) == 1:
            return z == self.width // 2
        else:
            return z in (self.width // 2 - 1, self.width // 2)

    @cache
    def _apply_rotation(self, state: BlockState):
        def rotate(match: Match) -> str:
            raw_dir = Direction[match.group(0)]
            rotated_dir = Direction(self.direction.rotate(raw_dir))
            return rotated_dir.name

        return DIRECTION_PATTERN.sub(rotate, state)

    def _get_theme(self, z: int) -> BlockState:
        theme_float_index = ((z + 0.5) * len(self.theme)) / self.width
        theme_index = int(theme_float_index)

        # Boundary cases are when z is exactly between two themes
        # => theme_float_index is an int
        if theme_index == theme_float_index:
            if self._theme_should_round_up:
                self._theme_should_round_up = False
            else:
                self._theme_should_round_up = True
                theme_index -= 1

        return self.theme[theme_index]
