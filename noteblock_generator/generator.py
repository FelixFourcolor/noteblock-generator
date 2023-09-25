from __future__ import annotations

import math
from enum import Enum
from typing import TYPE_CHECKING, Optional

import amulet

from .compiler import DYNAMIC_RANGE, Composition, Note, Rest, logger

if TYPE_CHECKING:
    from .main import Location, Orientation


class Block(amulet.api.block.Block):
    """A thin wrapper of amulet block, with a more convenient constructor"""

    def __init__(self, name: str, **properties):
        properties = {k: amulet.StringTag(v) for k, v in properties.items()}
        super().__init__("minecraft", name, properties)


class NoteBlock(Block):
    """A covenience class for noteblocks"""

    INSTRUMENTS = {
        "bass": Block("oak_log"),
        "didgeridoo": Block("pumpkin"),
        "guitar": Block("white_wool"),
        "harp": Block("air"),
        "bit": Block("emerald_block"),
        "banjo": Block("hay_block"),
        "iron_xylophone": Block("iron_block"),
        "pling": Block("glowstone"),
        "flute": Block("clay"),
        "cow_bell": Block("soul_sand"),
        "bell": Block("gold_block"),
        "xylophone": Block("bone_block"),
        "chime": Block("packed_ice"),
        "basedrum": Block("stone"),
        "hat": Block("glass"),
        "snare": Block("sand_stone"),
    }

    def __init__(self, _note: Note):
        super().__init__("note_block", note=_note.note, instrument=_note.instrument)
        self.base = self.INSTRUMENTS[_note.instrument]


class Direction(tuple[int, int], Enum):
    """Minecraft's cardinal directions"""

    # coordinates in (x, z)
    north = (0, -1)
    south = (0, 1)
    east = (1, 0)
    west = (-1, 0)

    def __neg__(self):
        match self:
            case (x, 0):
                return Direction((-x, 0))
            case (0, x):
                return Direction((0, -x))
            case _:
                raise NotImplementedError

    def __str__(self):
        return self.name


class Repeater(Block):
    """A convenience class for repeaters"""

    def __init__(self, delay: int, direction: Direction):
        # MiNECRAFT's BUG: repeater's direction is reversed
        super().__init__("repeater", delay=delay, facing=(-direction).name)


class Redstone(Block):
    """A convenience class for redstone wires"""

    def __init__(self, *connections: Direction):
        # only support connecting sideways,
        # because that's all we need for this build
        if not connections:
            # connected to all sides by default
            connections = tuple(Direction)
        super().__init__(
            "redstone_wire",
            **{direction.name: "side" for direction in connections},
        )


class World:
    """A thin wrapper of amulet World,
    with convenient methods to load, set blocks, and save.
    """

    _VERSION = ("java", (1, 20))
    # TODO: make this a command-line argument

    _dimension: str

    def __init__(self, path: str):
        self._path = str(path)

    def __enter__(self):
        self._level = (level := amulet.load_level(self._path))
        self.players = list(map(level.get_player, level.all_player_ids()))
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        logger.info("Almost there...")
        if exc_type is None and self._level.changed:
            self._level.save()
        self._level.close()

    def __getitem__(self, coordinates: tuple[int, int, int]):
        return self._level.get_version_block(
            *coordinates, self.dimension, self._VERSION
        )[0]

    def __setitem__(self, coordinates: tuple[int, int, int], block: Block):
        self._level.set_version_block(
            *coordinates, self.dimension, self._VERSION, block
        )

    def generate(
        self,
        *,
        composition: Composition,
        location: Location,
        dimension: Optional[str],
        orientation: Orientation,
        theme: str,
        clear=False,
    ):
        def equalize_voice_length():
            for voice in composition:
                rest = Rest(voice)
                for _ in range(voice.division - len(voice[-1])):
                    voice[-1].append(rest)
                for _ in range(LONGEST_VOICE_LENGTH - len(voice)):
                    voice.append([rest] * voice.division)

        def generate_space():
            def generate_walking_glass():
                self[X0 + x_increment * x, y_glass, Z0 + z_increment * z] = glass
                for y in mandatory_clear_range:
                    self[
                        X0 + x_increment * x,
                        y,
                        Z0 + z_increment * z,
                    ] = air

            def clear_space():
                for y in optional_clear_range:
                    self[
                        X0 + x_increment * x,
                        y,
                        Z0 + z_increment * z,
                    ] = air

            def remove_dangerous_blocks():
                for y in optional_clear_range:
                    if (
                        self[
                            X0 + x_increment * x,
                            y,
                            Z0 + z_increment * z,
                        ].base_name
                        in DANGER_LIST
                    ):
                        self[
                            X0 + x_increment * x,
                            y,
                            Z0 + z_increment * z,
                        ] = air

            glass = Block("glass")

            DANGER_LIST = (
                "anvil",
                "comparator",
                "concrete_powder",
                "dragon_egg",
                "gravel",
                "lava",
                "note_block",
                "observer",
                "piston",
                "pointed_dripstone",
                "red_sand",
                "redstone_block",
                "redstone_torch",
                "redstone_wire",
                "repeater",
                "sand",
                "sticky_piston",
                "suspicious_sand",
                "suspicious_gravel",
                "tnt",
                "tnt_minecart",
                "water",
            )

            mandatory_clear_range = [y_glass + 2, y_glass + 1]
            optional_clear_range = range(
                y_glass - VOICE_HEIGHT * (len(composition) + 1), y_glass
            )

            Z_MAX = composition.division * NOTE_LENGTH + DIVISION_CHANGING_LENGTH + 2
            X_MAX = (LONGEST_VOICE_LENGTH + INIT_DIVISIONS) * DIVISION_WIDTH + 1
            for z in range(Z_MAX + 1):
                for x in range(X_MAX + 1):
                    generate_walking_glass()
                    if clear or x in (0, X_MAX) or z in (0, Z_MAX):
                        clear_space()
                    else:
                        remove_dangerous_blocks()

        def generate_init_system():
            for voice in composition:
                for _ in range(INIT_DIVISIONS):
                    voice.insert(0, [Rest(voice, delay=1)] * voice.division)

            x = X0 + x_increment * (DIVISION_WIDTH // 2)
            y = y_glass
            z = Z0 + z_increment
            self[x + x_increment, y - 3, z] = block
            self[x + x_increment, y - 2, z] = Redstone(z_direction, -x_direction)
            self[x + x_increment, y - 1, z] = air
            self[x, y - 2, z] = block
            self[x, y - 1, z] = Redstone(x_direction, -x_direction)
            self[x, y, z] = block
            self[x, y + 1, z] = Block("oak_button", face="floor", facing=-x_direction)

        def generate_redstones():
            self[x, y, z] = block
            self[x, y + 1, z] = Repeater(note.delay, z_direction)
            self[x, y + 1, z + z_increment] = block
            self[x, y + 2, z + z_increment] = Redstone()
            self[x, y + 2, z + z_increment * 2] = block

        def generate_noteblocks():
            # place noteblock positions in this order, depending on dynamic
            positions = [-x_increment, x_increment, -2 * x_increment, 2 * x_increment]
            if note.dynamic:
                noteblock = NoteBlock(note)
                for i in range(note.dynamic):
                    self[x + positions[i], y + 2, z + z_increment] = noteblock
                    if not clear:
                        self[x + positions[i], y + 1, z + z_increment] = noteblock.base
                        self[x + positions[i], y + 3, z + z_increment] = air

        def generate_division_changing_system():
            self[x, y, z + z_increment * 2] = block
            self[x, y + 1, z + z_increment * 2] = Redstone(z_direction, -z_direction)
            self[x, y, z + z_increment * 3] = block
            self[x, y + 1, z + z_increment * 3] = Redstone(x_direction, -z_direction)
            for i in range(1, DIVISION_WIDTH):
                self[x + x_increment * i, y, z + z_increment * 3] = block
                self[x + x_increment * i, y + 1, z + z_increment * 3] = Redstone(
                    x_direction, -x_direction
                )
            self[x + x_increment * DIVISION_WIDTH, y, z + z_increment * 3] = block
            self[
                x + x_increment * DIVISION_WIDTH, y + 1, z + z_increment * 3
            ] = Redstone(-z_direction, -x_direction)

        if not composition:
            return

        NOTE_LENGTH = 2
        DIVISION_WIDTH = DYNAMIC_RANGE.stop  # 4 noteblocks + 1 stone in the middle
        VOICE_HEIGHT = 2
        DIVISION_CHANGING_LENGTH = 2  # how many blocks it takes to wrap around each bar
        LONGEST_VOICE_LENGTH = max(map(len, composition))
        # add this number of divisions to the beginning of every voice
        # so that with a push of a button, all voices start at the same time
        INIT_DIVISIONS = math.ceil((len(composition) - 1) / composition.division)

        try:
            player_location = tuple(map(math.floor, self.players[0].location))
        except IndexError:
            player_location = (0, 0, 0)
        X0, Y0, Z0 = location
        if location.x.relative:
            X0 += player_location[0]
        if location.y.relative:
            Y0 += player_location[1]
        if location.z.relative:
            Z0 += player_location[2]
        if dimension is None:
            try:
                dimension = self.players[0].dimension
            except IndexError:
                dimension = "minecraft:overworld"
        self.dimension = dimension

        x_direction = Direction((1, 0))
        if not orientation.x:
            x_direction = -x_direction
        x_increment = x_direction[0]
        y_increment = 1
        if orientation.y:
            y_glass = Y0 + VOICE_HEIGHT * (len(composition) + 1)
        else:
            y_increment = -y_increment
            Y0 += 1  # count from player's head rather than feet
            y_glass = Y0 - VOICE_HEIGHT
        z_direction = Direction((0, 1))
        if not orientation.z:
            z_direction = -z_direction
        z_increment = z_direction[1]

        air = Block("air")
        block = Block(theme)

        equalize_voice_length()
        generate_space()
        generate_init_system()

        for i, voice in enumerate(composition[::-1]):
            y = y_glass - VOICE_HEIGHT * (i + 2)
            z = Z0 + z_increment * (DIVISION_CHANGING_LENGTH + 2)

            for j, division in enumerate(voice):
                x = X0 + x_increment * (1 + DIVISION_WIDTH // 2 + j * DIVISION_WIDTH)
                z_increment = z_direction[1]
                z0 = z - z_increment * DIVISION_CHANGING_LENGTH
                self[x, y + 2, z0] = block

                for k, note in enumerate(division):
                    z = z0 + k * z_increment * NOTE_LENGTH
                    generate_redstones()
                    generate_noteblocks()

                # if there is a next division, change division and flip direction
                try:
                    voice[j + 1]
                except IndexError:
                    pass
                else:
                    generate_division_changing_system()
                    z_direction = -z_direction

            # if number of division is even
            if len(voice) % 2 == 0:
                # z_direction has been flipped, reset it to original
                z_direction = -z_direction
                z_increment = z_direction[1]


def generate(path_out, **kwargs):
    with World(path_out) as world:
        world.generate(**kwargs)
