from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Literal

from .coordinates import XZ

if TYPE_CHECKING:
    DirectionName = Literal["north", "south", "east", "west"]


class Direction(XZ, Enum):
    # coordinates in (x, z)
    north = (0, -1)
    south = (0, 1)
    east = (1, 0)
    west = (-1, 0)

    def rotate(self, other: XZ) -> XZ:
        # Complex multiplication, with (x, z) representing x + zi
        return (
            self[0] * other[0] - self[1] * other[1],
            self[0] * other[1] + self[1] * other[0],
        )

    def __str__(self):
        return {
            Direction.north: "towards negative Z",
            Direction.south: "towards positive Z",
            Direction.east: "towards positive X",
            Direction.west: "towards negative X",
        }[self]


DIRECTION_NAMES: list[DirectionName] = ["north", "south", "east", "west"]

_ROTATION_MAP = {
    -180: Direction.north,
    -90: Direction.east,
    0: Direction.south,
    90: Direction.west,
    180: Direction.north,
}


def get_nearest_direction(rotation: float):
    match = min(_ROTATION_MAP.keys(), key=lambda x: abs(x - rotation))
    direction = _ROTATION_MAP[match]
    return direction
