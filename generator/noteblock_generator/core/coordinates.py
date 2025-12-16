from __future__ import annotations

from typing import NamedTuple

from ..cli.args import Align, Tilt
from .placement import Placement

XYZ = tuple[int, int, int]
XZ = tuple[int, int]


class Bounds(NamedTuple):
    min_x: int
    max_x: int
    min_y: int
    max_y: int
    min_z: int
    max_z: int


class CoordinateTranslator(Placement):
    def get(self, coords: XYZ) -> XYZ:
        raw_x, raw_y, raw_z = coords

        match self.align:
            case Align.center:
                shifted_z = raw_z - (self.width - 1) // 2
            case Align.left:
                shifted_z = raw_z - self.width + 1
            case Align.right:
                shifted_z = raw_z

        rotated_x, rotated_z = self.direction.rotate((raw_x, shifted_z))

        translated_x = self.origin_x + rotated_x
        translated_y = self.origin_y + raw_y
        translated_z = self.origin_z + rotated_z

        if self.tilt == Tilt.down:
            translated_y -= self.height - 2

        return translated_x, translated_y, translated_z

    def calculate_bounds(self):
        start_x, start_y, start_z = self.get((0, 0, 0))
        end_x, end_y, end_z = self.get((
            self.length - 1,
            self.height - 1,
            self.width - 1,
        ))
        return Bounds(
            min_x=min(start_x, end_x),
            max_x=max(start_x, end_x),
            min_y=min(start_y, end_y),
            max_y=max(start_y, end_y),
            min_z=min(start_z, end_z),
            max_z=max(start_z, end_z),
        )
