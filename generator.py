import math
from enum import Enum

import amulet as _amulet

from music import INSTRUMENTS, Composition, Rest

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


class Direction(tuple[int, int], Enum):
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

    def __str__(self):
        return self.name


class Repeater(Block):
    def __init__(self, delay: int, direction: Direction):
        if delay not in range(1, 5):
            raise ValueError("delay must be in range(1, 5).")
        # Minecraft's bug: repeater's direction is reversed
        super().__init__("repeater", delay=delay, facing=(-direction).name)


class Redstone(Block):
    def __init__(
        self,
        connections=list(Direction),
    ):
        super().__init__(
            "redstone_wire",
            **{direction.name: "side" for direction in connections},
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

    def __setitem__(self, coordinates: tuple[int, int, int], block: Block):
        self._level.set_version_block(*coordinates, _namespace, _version, block)


def generate(composition: Composition, path: str):
    def clear_space():
        longest_voice = max(map(len, composition)) + init_length
        longest_bar = max(map(lambda voice: max(map(len, voice)), composition))
        for x in range(-1, 5 * longest_voice + 1):
            for z in range(-1, 2 * longest_bar + 3):
                world[x, -1, z] = Stone
                for y in range(2 * len(composition) + 1):
                    world[x, y, z] = Air

    def generate_init_system():
        for voice in composition:
            for _ in range(init_length):
                voice.insert(0, [Rest(voice, tempo=1)] * composition.time)
        world[1, 2 * len(composition) - 1, 1] = Block("oak_button", facing=-x_direction)

    def generate_skeleton():
        world[x, y, z] = Repeater(note.delay, z_direction)
        world[x, y, z + z_i] = Stone
        world[x, y + 1, z + z_i * 2] = Stone

    def generate_notes():
        x_i = [1, -1, 2, -2]  # noteblock build order
        world[x, y + 1, z + z_i] = Redstone()
        for k in range(note.dynamic):
            world[x + x_i[k], y + 1, z + z_i] = NoteBlock(note.note, note.instrument)

    def generate_bar_change():
        world[x, y - 1, z + z_i * 2] = Stone
        world[x, y, z + z_i * 2] = Redstone((z_direction, -z_direction))
        world[x, y - 1, z + z_i * 3] = Stone
        world[x, y, z + z_i * 3] = Redstone((x_direction, -z_direction))
        for i in range(1, 5):
            world[x + i, y - 1, z + z_i * 3] = Stone
            world[x + i, y, z + z_i * 3] = Redstone((x_direction, -x_direction))
        world[x + 5, y - 1, z + z_i * 3] = Stone
        world[x + 5, y, z + z_i * 3] = Redstone((-z_direction, -x_direction))

    if not composition:
        return

    Air = Block("air")
    Stone = Block("stone")

    x_direction = Direction((1, 0))
    init_length = math.ceil((len(composition) - 1) / composition.time)

    with World(path) as world:
        clear_space()
        generate_init_system()

        for i, voice in enumerate(composition):
            y = 2 * i  # each voice takes 2 blocks of height
            z = 1
            for j, bar in enumerate(voice):
                x = 5 * j + 2  # each bar takes 5 blocks of width
                if j % 2 == 0:  # build direction alternates each bar
                    z_i = 1
                    z0 = 1
                else:
                    z_i = -1
                    z0 = z + 2
                z_direction = Direction((0, z_i))

                world[x, y + 1, z0] = Stone
                for k, note in enumerate(bar):
                    z = z0 + 2 * k * z_i  # each note takes 2 blocks of length
                    generate_skeleton()
                    generate_notes()
                try:
                    voice[j + 1]
                    generate_bar_change()
                except IndexError:
                    pass
