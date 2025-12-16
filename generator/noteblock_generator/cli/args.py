from enum import Enum


class Walkable(Enum):
    full = "full"
    partial = "partial"
    no = "no"


class Dimension(Enum):
    overworld = "overworld"
    nether = "nether"
    the_end = "the_end"


class Facing(Enum):
    north = "-z"
    south = "+z"
    east = "+x"
    west = "-x"


class Tilt(Enum):
    up = "up"
    down = "down"


class Align(Enum):
    left = "left"
    center = "center"
    right = "right"
