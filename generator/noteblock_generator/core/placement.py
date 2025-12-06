from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ..data.schema import BlockState, Size
    from .coordinates import XYZ
    from .direction import Direction

    TiltName = Literal["up", "down"]
    AlignName = Literal["left", "center", "right"]


@dataclass(frozen=True)
class PlacementConfig:
    origin: XYZ
    facing: Direction
    tilt: TiltName
    align: AlignName
    theme: list[BlockState]
    blend: bool


class PlacementMapper(ABC):
    def __init__(self, config: PlacementConfig):
        self.origin_x, self.origin_y, self.origin_z = config.origin
        self.facing = config.facing
        self.tilt: TiltName = config.tilt
        self.align: AlignName = config.align
        self.theme = config.theme
        self.empty_block: BlockState | None = None if config.blend else "air"

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
