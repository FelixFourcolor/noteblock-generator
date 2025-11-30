from __future__ import annotations

import math
import re
from functools import cache
from itertools import chain, product
from typing import TYPE_CHECKING

from .direction import DIRECTION_NAMES, Direction
from .placement import PlacementTranslator

if TYPE_CHECKING:
    from re import Match

    from ..data.schema import BlockMap, BlockState, BlockType, Size, ThemeBlock


DIRECTION_PATTERN = re.compile("|".join(DIRECTION_NAMES))
THEME_BLOCK: ThemeBlock = 0


class BlockTranslator(PlacementTranslator):
    def update_size(self, size: Size):
        super().update_size(size)
        # to alternate rounding in boundary cases
        self._theme_should_round_up = True

    def calculate_fill(self, prev_size: Size) -> BlockMap:
        if prev_size == self.size:
            return {}

        prev_length = prev_size.length
        prev_height = prev_size.height
        prev_width = prev_size.width

        x_expansion = range(prev_length, self.length)
        match self.tilt:
            case "down":
                y_expansion = range(self.height - prev_height)
            case "up":
                y_expansion = range(prev_height, self.height)
        match self.align:
            case "center":
                offset = math.floor((self.width - prev_width) // 2)
                z_expansion = chain(
                    range(offset), range(prev_width + offset, self.width)
                )
            case "left":
                z_expansion = range(self.width - prev_width)
            case "right":
                z_expansion = range(prev_width, self.width)

        return {
            f"{x} {y} {z}": self.empty_block
            for (x, y, z) in chain(
                product(x_expansion, range(self.height), range(self.width)),
                product(range(self.length), y_expansion, range(self.width)),
                product(range(self.length), range(self.height), z_expansion),
            )
        }

    def __getitem__(self, arg: tuple[BlockType, int]):
        block, z = arg

        if block is None:
            return self.empty_block

        if block == THEME_BLOCK:
            block = self._get_theme(z)
        return self._apply_rotation(block)

    @cache
    def _apply_rotation(self, state: BlockState):
        def rotate(match: Match) -> str:
            raw_dir = Direction[match.group(0)]
            rotated_dir = Direction(self.facing.rotate(raw_dir))
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
