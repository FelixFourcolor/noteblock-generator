from enum import Enum
from typing import Iterable

import amulet as _amulet

from music import INSTRUMENTS, Composition

_namespace = "minecraft:overworld"
_version = ("java", (1, 20))


class Block(_amulet.api.block.Block):
    def __init__(self, name: str, **properties):
        properties = {k: _amulet.StringTag(v) for k, v in properties.items()}
        super().__init__("minecraft", name, properties)


class NoteBlock(Block):
    def __init__(self, note: int, instrument="harp"):
        if note not in range(25):
            raise ValueError("note must be in range(25).")
        if instrument not in INSTRUMENTS:
            raise ValueError(f"{instrument} is not a valid instrument.")
        super().__init__("note_block", note=note, instrument=instrument)


class Direction(Enum):
    north = (0, -1)
    south = (0, 1)
    east = (1, 0)
    west = (-1, 0)

    def __neg__(self):
        match self:
            case Direction.north:
                return Direction.south
            case Direction.south:
                return Direction.north
            case Direction.east:
                return Direction.west
            case Direction.west:
                return Direction.east
            case _:
                return NotImplemented


DirectionType = Direction | tuple[int, int]


class Repeater(Block):
    def __init__(self, delay: int, direction: DirectionType):
        if delay not in range(1, 5):
            raise ValueError("delay must be in range(1, 5).")
        # Minecraft's bug: repeater's direction is reversed
        match Direction(direction):
            case Direction.south:
                facing = "north"
            case Direction.north:
                facing = "south"
            case Direction.west:
                facing = "east"
            case Direction.east:
                facing = "west"
            case _ as x:
                raise ValueError(f"Invalid direction: {x}.")
        super().__init__("repeater", delay=delay, facing=facing)


class Redstone(Block):
    # redstone wire, connected to all sides by default
    def __init__(
        self,
        connections: Iterable[DirectionType] = list(Direction),
    ):
        super().__init__(
            "redstone_wire",
            **{direction.name: "side" for direction in map(Direction, connections)},
        )


class World:
    def __init__(self, path: str):
        self._path = path

    def __enter__(self):
        self._level = _amulet.load_level(self._path)
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is None and self._level.changed:
            self._level.save()
        self._level.close()

    def __getitem__(self, coordinates: tuple[int, int, int]):
        return self._level.get_version_block(*coordinates, _namespace, _version)

    def __setitem__(self, coordinates: tuple[int, int, int], block: Block | str):
        if isinstance(_block := block, str):
            _block = Block(_block)
        self._level.set_version_block(*coordinates, _namespace, _version, _block)


def generate(composition: Composition, path: str):
    def generate_skeleton():
        world[x, y, z] = Repeater(note.delay, z_direction)
        world[x, y, z + z_i] = Block("stone")
        world[x, y + 1, z + z_i * 2] = Block("stone")

    def generate_notes():
        x_i = [1, -1, 2, -2]  # noteblock build order
        world[x, y + 1, z + z_i] = Redstone()
        for k in range(note.dynamic):
            world[x + x_i[k], y + 1, z + z_i] = NoteBlock(note.note, note.instrument)

    def generate_bar_change():
        world[x, y, z + z_i * 2] = Redstone((z_direction, -z_direction))
        world[x, y, z + z_i * 3] = Redstone((x_direction, -z_direction))
        world[x + 1, y, z + z_i * 3] = Redstone((x_direction, -x_direction))
        world[x + 2, y, z + z_i * 3] = Redstone((x_direction, -x_direction))
        world[x + 3, y, z + z_i * 3] = Redstone((x_direction, -x_direction))
        world[x + 4, y, z + z_i * 3] = Redstone((x_direction, -x_direction))
        world[x + 5, y, z + z_i * 3] = Redstone((-z_direction, -x_direction))

    x_direction = Direction((1, 0))
    with World(path) as world:
        for i, voice in enumerate(composition):
            y = 2 * i  # each voice takes 2 blocks of height
            for j, bar in enumerate(voice):
                x = 5 * j  # each bar takes 5 blocks of width
                if j % 2 == 0:  # build direction alternates each bar
                    z_i = 1
                    z0 = 0
                else:
                    z_i = -1
                    z0 = 2 * len(bar)
                z_direction = Direction((0, z_i))

                world[x, y + 1, z0] = Block("stone")
                for k, note in enumerate(bar):
                    z = z0 + 2 * k * z_i  # each note takes 2 blocks of length
                    generate_skeleton()
                    generate_notes()
                try:
                    voice[j + 1]
                    generate_bar_change()
                except IndexError:
                    pass
