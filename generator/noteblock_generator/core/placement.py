from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..cli.args import Align, Tilt, Walkable
    from ..data.schema import BlockState, Size
    from .coordinates import XYZ
    from .direction import Direction


@dataclass(frozen=True)
class PlacementConfig:
    origin: XYZ
    direction: Direction
    tilt: Tilt
    align: Align
    theme: list[BlockState]
    walkable: Walkable
    preserve_terrain: bool


class Placement(ABC):
    def __init__(self, config: PlacementConfig):
        self.origin_x, self.origin_y, self.origin_z = config.origin
        self.direction = config.direction
        self.tilt = config.tilt
        self.align = config.align
        self.theme = config.theme
        self.walkable = config.walkable
        self.empty_block: BlockState | None = None if config.preserve_terrain else "air"

        self.size: Size | None = None

    def update_size(self, size: Size):
        self.size = size

    @property
    def length(self) -> int:
        if self.size is None:
            raise ValueError("Size has not been set.")
        return self.size.length

    @property
    def height(self) -> int:
        if self.size is None:
            raise ValueError("Size has not been set.")
        return self.size.height

    @property
    def width(self) -> int:
        if self.size is None:
            raise ValueError("Size has not been set.")
        return self.size.width
