from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Literal

from typing_extensions import override

if TYPE_CHECKING:
    DirectionName = Literal["north", "south", "east", "west"]
    TiltName = Literal["up", "down"]


XYZ = tuple[int, int, int]
XZ = tuple[int, int]


class Direction(XZ, Enum):
    # coordinates in (x, z)
    north = (0, -1)
    south = (0, 1)
    east = (1, 0)
    west = (-1, 0)

    @override
    def __str__(self):
        return self.name

    def rotate(self, vector: XZ) -> XZ:
        """Complex multiplication, with (x, z) representing x + zi"""
        return (
            self[0] * vector[0] - self[1] * vector[1],
            self[0] * vector[1] + self[1] * vector[0],
        )

    @property
    def description(self):
        return {
            Direction.north: "towards negative Z",
            Direction.south: "towards positive Z",
            Direction.east: "towards positive X",
            Direction.west: "towards negative X",
        }[self]


DIRECTION_NAMES: list[DirectionName] = ["north", "south", "east", "west"]

ROTATION_TO_DIRECTION_MAP = {
    -180: Direction.north,
    -90: Direction.east,
    0: Direction.south,
    90: Direction.west,
    180: Direction.north,
}


def get_nearest_direction(rotation: float):
    match = min(ROTATION_TO_DIRECTION_MAP.keys(), key=lambda x: abs(x - rotation))
    direction = ROTATION_TO_DIRECTION_MAP[match]
    return direction
