import math
from enum import Enum
from pathlib import Path

import amulet as _amulet

from translator import INSTRUMENTS, MAX_DYNAMIC, Composition, Note, Rest

_namespace = "minecraft:overworld"
_version = ("java", (1, 20))


class Block(_amulet.api.block.Block):
    def __init__(self, name: str, **properties):
        properties = {k: _amulet.StringTag(v) for k, v in properties.items()}
        super().__init__("minecraft", name, properties)


class NoteBlock(Block):
    def __init__(self, _note: Note):
        if (note := _note.note) not in range(25):
            raise ValueError("note must be in range(25).")
        if (instrument := _note.instrument) not in INSTRUMENTS:
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
    def __init__(self, path: str | Path):
        self._path = str(path)

    def __enter__(self):
        self._level = (level := _amulet.load_level(self._path))
        self.players = list(map(level.get_player, level.all_player_ids()))
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is None and self._level.changed:
            self._level.save()
        self._level.close()

    def __setitem__(self, coordinates: tuple[int, int, int], block: Block):
        self._level.set_version_block(*coordinates, _namespace, _version, block)


def generate(
    composition: Composition, path: str | Path, location: tuple[float, float, float]
):
    def generate_space():
        notes = max(map(lambda voice: max(map(len, voice)), composition))
        bars = max(map(len, composition)) + INIT_BARS
        voices = len(composition)
        for z in range(notes * NOTE_LENGTH + BAR_CHANGING_TOTAL_LENGTH + 2 * MARGIN):
            for x in range(bars * BAR_WIDTH + 2 * MARGIN):
                world[X0 + x, Y0, Z0 + z] = Stone
                for y in range(1, voices * VOICE_HEIGHT + 2 * MARGIN):
                    world[X0 + x, Y0 + y, Z0 + z] = Air

    def generate_init_system():
        for voice in composition:
            for _ in range(INIT_BARS):
                voice.insert(0, [Rest(voice, tempo=1)] * composition.time)
        # so that with a push of this button, all voices start at the same time
        world[X0 + 2, Y0 + 2 * len(composition), Z0 + 2] = Block(
            "oak_button", facing=-x_direction
        )

    def generate_redstones():
        world[x, y, z] = Repeater(note.delay, z_direction)
        world[x, y, z + z_increment] = Stone
        world[x, y + 1, z + z_increment] = Redstone()
        world[x, y + 1, z + z_increment * 2] = Stone

    def generate_noteblocks():
        # place noteblock positions in this order, depending on dynamic
        positions = [1, -1, 2, -2]
        for i in range(note.dynamic):
            world[x + positions[i], y + 1, z + z_increment] = NoteBlock(note)

    def generate_bar_changing_system():
        world[x, y - 1, z + z_increment * 2] = Stone
        world[x, y, z + z_increment * 2] = Redstone((z_direction, -z_direction))
        world[x, y - 1, z + z_increment * 3] = Stone
        world[x, y, z + z_increment * 3] = Redstone((x_direction, -z_direction))
        for i in range(1, BAR_WIDTH):
            world[x + i, y - 1, z + z_increment * 3] = Stone
            world[x + i, y, z + z_increment * 3] = Redstone((x_direction, -x_direction))
        world[x + 5, y - 1, z + z_increment * 3] = Stone
        world[x + 5, y, z + z_increment * 3] = Redstone((-z_direction, -x_direction))

    if not composition:
        return

    MARGIN = 1
    NOTE_LENGTH = 2
    BAR_WIDTH = MAX_DYNAMIC + 1  # MAX_DYNAMIC noteblocks + stone
    VOICE_HEIGHT = 2
    BAR_CHANGING_LENGTH = 2  # how many blocks it takes to wrap around and change bar
    BAR_CHANGING_TOTAL_LENGTH = BAR_CHANGING_LENGTH + 1  # 1 for z-offset every change
    # add this number of bars to the beginning of every voice
    INIT_BARS = math.ceil((len(composition) - 1) / composition.time)

    with World(path) as world:
        Stone = Block("stone")
        Air = Block("air")

        x_direction = Direction((1, 0))
        if not location:
            location = world.players[0].location
        X0, Y0, Z0 = map(math.floor, location)

        generate_space()
        generate_init_system()

        for i, voice in enumerate(composition):
            y = Y0 + MARGIN + i * VOICE_HEIGHT
            z = Z0 + MARGIN + BAR_CHANGING_TOTAL_LENGTH
            z_direction = Direction((0, 1))

            for j, bar in enumerate(voice):
                x = X0 + MARGIN + MAX_DYNAMIC // 2 + j * BAR_WIDTH
                z_increment = z_direction[1]
                z0 = z - z_increment * BAR_CHANGING_LENGTH

                world[x, y + 1, z0] = Stone
                for k, note in enumerate(bar):
                    z = z0 + k * z_increment * NOTE_LENGTH
                    generate_redstones()
                    generate_noteblocks()
                try:
                    voice[j + 1]
                except IndexError:
                    pass
                else:
                    generate_bar_changing_system()
                    z_direction = -z_direction
