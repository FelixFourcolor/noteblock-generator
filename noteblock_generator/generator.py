from __future__ import annotations

import math
from enum import Enum
from typing import Optional

import amulet

from .compiler import DYNAMIC_RANGE, Composition, Note, Rest, Voice, logger
from .main import Location, Orientation

_Block = amulet.api.Block
_Level = amulet.api.level.World | amulet.api.level.Structure


class Block(_Block):
    """A thin wrapper of amulet block, with a more convenient constructor"""

    def __init__(self, name: str, **properties):
        properties = {k: amulet.StringTag(v) for k, v in properties.items()}
        super().__init__("minecraft", name, properties)


class NoteBlock(Block):
    """A covenience class for noteblocks"""

    def __init__(self, _note: Note):
        super().__init__("note_block", note=_note.note, instrument=_note.instrument)


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
    _level: _Level

    def __init__(self, path: str):
        self._path = str(path)

    def __enter__(self):
        self._level = (level := amulet.load_level(self._path))
        self.players = list(map(level.get_player, level.all_player_ids()))
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        logger.info("Finishing up...")
        if exc_type is None and self._level.changed:
            self._level.save()
        self._level.close()

    def __getitem__(self, coordinates: tuple[int, int, int]):
        return self._level.get_version_block(
            *coordinates, self._dimension, self._VERSION
        )[0]

    def __setitem__(self, coordinates: tuple[int, int, int], block: _Block):
        self._level.set_version_block(
            *coordinates, self._dimension, self._VERSION, block
        )

    def generate(
        self,
        *,
        composition: Composition,
        location: Location,
        dimension: Optional[str],
        orientation: Orientation,
        theme: str,
        clear: bool,
    ):
        def generate_init_system_for_single_orchestra():
            button = Block("oak_button", face="floor", facing=-x_direction)
            redstone = Redstone(z_direction, -z_direction)

            x = X + x_increment * math.ceil(DIVISION_WIDTH / 2)
            y = y_glass

            self[x, y - 3, Z + z_increment] = block
            self[x, y - 2, Z + z_increment] = redstone
            self[x, y - 1, Z + z_increment] = air
            self[x, y - 1, Z + z_increment * 2] = redstone
            self[x, y - 1, Z + z_increment * 3] = block

            self[x, y, Z + z_increment * 2] = block
            self[x, y + 1, Z + z_increment * 2] = button

        def generate_init_system_for_double_orchestras(x0: int):
            def generate_bridge(z: int, z_direction: Direction):
                z_increment = z_direction[1]

                repeater = Repeater(delay=1, direction=-z_direction)
                self[x, y - 3, z + z_increment] = block
                self[x, y - 2, z + z_increment] = redstone
                self[x, y - 1, z + z_increment] = air
                self[x, y - 2, z + z_increment * 2] = block
                self[x, y - 1, z + z_increment * 2] = redstone
                self[x, y - 1, z + z_increment * 3] = block
                self[x, y, z + z_increment * 3] = redstone

                for i in range(4, math.ceil(Z_BOUNDARY / 2) + 1):
                    if x0 == 0 or i == 4:
                        self[x, y, z + z_increment * i] = block
                    self[x, y + 1, z + z_increment * i] = (
                        redstone if i % 16 else repeater
                    )

            def generate_button():
                z = Z + z_increment * (1 - math.ceil(Z_BOUNDARY / 2))
                button = Block("oak_button", face="floor", facing=-x_direction)
                if x0 == 0 or composition.division == 1:
                    self[x, y, z] = block
                self[x, y + 1, z] = button

            x = X + x0 + x_increment * math.ceil(DIVISION_WIDTH / 2)
            y = y_glass
            redstone = Redstone(z_direction, -z_direction)

            generate_bridge(Z - z_increment * Z_BOUNDARY, z_direction)
            generate_bridge(Z + z_increment * 2, -z_direction)
            generate_button()

        def generate_orchestra(voices: list[Voice], z_direction: Direction):
            if not voices:
                return

            def generate_space():
                def generate_walking_glass():
                    self[X + x_increment * x, y_glass, Z + z_increment * z] = glass
                    for y in mandatory_clear_range:
                        self[
                            X + x_increment * x,
                            y,
                            Z + z_increment * z,
                        ] = air

                def clear_space():
                    for y in optional_clear_range:
                        self[
                            X + x_increment * x,
                            y,
                            Z + z_increment * z,
                        ] = air

                def remove_dangerous_blocks():
                    for y in optional_clear_range:
                        coordinates = (
                            X + x_increment * x,
                            y,
                            Z + z_increment * z,
                        )
                        suspect = self[coordinates]
                        if not isinstance(suspect, _Block):
                            continue
                        if suspect.base_name in REMOVE_LIST:
                            self[coordinates] = air
                        else:
                            self[coordinates] = suspect.base_block

                glass = Block("glass")

                REMOVE_LIST = (
                    "anvil",
                    "bubble_column",
                    "calibrated_sculk_sensor",
                    "comparator",
                    "concrete_powder",
                    "dragon_egg",
                    "gravel",
                    "jukebox",
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
                    "sculk_sensor",
                    "seagrass",
                    "sticky_piston",
                    "suspicious_sand",
                    "suspicious_gravel",
                    "tall_seagrass",
                    "tnt",
                    "tnt_minecart",
                    "water",
                )

                mandatory_clear_range = [y_glass + 2, y_glass + 1]
                optional_clear_range = range(Y_BOUNDARY, y_glass)

                for z in range(Z_BOUNDARY + 1):
                    for x in range(X_BOUNDARY + 1):
                        generate_walking_glass()
                        if clear or x in (0, X_BOUNDARY) or z in (0, Z_BOUNDARY):
                            clear_space()
                        else:
                            remove_dangerous_blocks()

            def generate_redstones():
                self[x, y, z] = block
                self[x, y + 1, z] = Repeater(note.delay, z_direction)
                self[x, y + 1, z + z_increment] = block
                self[x, y + 2, z + z_increment] = Redstone()
                self[x, y + 2, z + z_increment * 2] = block

            def generate_noteblocks():
                # place noteblock positions in this order, depending on dynamic
                positions = [
                    -x_increment,
                    x_increment,
                    -2 * x_increment,
                    2 * x_increment,
                ]
                if note.dynamic:
                    noteblock = NoteBlock(note)
                    for i in range(note.dynamic):
                        self[x + positions[i], y + 2, z + z_increment] = noteblock
                        if not clear:
                            self[x + positions[i], y + 1, z + z_increment] = air
                            self[x + positions[i], y + 3, z + z_increment] = air

            def generate_division_bridge():
                self[x, y, z + z_increment * 2] = block
                self[x, y + 1, z + z_increment * 2] = Redstone(
                    z_direction, -z_direction
                )
                self[x, y, z + z_increment * 3] = block
                self[x, y + 1, z + z_increment * 3] = Redstone(
                    x_direction, -z_direction
                )
                for i in range(1, DIVISION_WIDTH):
                    self[x + x_increment * i, y, z + z_increment * 3] = block
                    self[x + x_increment * i, y + 1, z + z_increment * 3] = Redstone(
                        x_direction, -x_direction
                    )
                self[x + x_increment * DIVISION_WIDTH, y, z + z_increment * 3] = block
                self[
                    x + x_increment * DIVISION_WIDTH, y + 1, z + z_increment * 3
                ] = Redstone(-z_direction, -x_direction)

            z_increment = z_direction[1]
            generate_space()

            for i, voice in enumerate(voices[::-1]):
                for _ in range(INIT_DIVISIONS):
                    voice.insert(0, [Rest(voice, delay=1)] * voice.division)

                y = y_glass - VOICE_HEIGHT * (i + 1) - 2
                z = Z + z_increment * (DIVISION_CHANGING_LENGTH + 2)

                for j, division in enumerate(voice):
                    x = X + x_increment * (1 + DIVISION_WIDTH // 2 + j * DIVISION_WIDTH)
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
                        generate_division_bridge()
                        z_direction = -z_direction

                # if number of division is even
                if len(voice) % 2 == 0:
                    # z_direction has been flipped, reset it to original
                    z_direction = -z_direction
                    z_increment = z_direction[1]

        air = Block("air")
        block = Block(theme)

        NOTE_LENGTH = 2
        DIVISION_WIDTH = DYNAMIC_RANGE.stop  # 4 noteblocks + 1 stone in the middle
        VOICE_HEIGHT = 2
        DIVISION_CHANGING_LENGTH = 2  # how many blocks it takes to wrap around each bar
        # add this number of divisions to the beginning of every voice
        # so that with a push of a button, all voices start at the same time
        INIT_DIVISIONS = math.ceil((composition.size - 1) / composition.division)

        try:
            player_location = tuple(map(math.floor, self.players[0].location))
        except IndexError:
            player_location = (0, 0, 0)
        X, Y, Z = location
        if location.x.relative:
            X += player_location[0]
        if location.y.relative:
            Y += player_location[1]
        if location.z.relative:
            Z += player_location[2]
        if dimension is not None:
            self._dimension = dimension
        else:
            try:
                self._dimension = self.players[0].dimension
            except IndexError:
                self._dimension = "minecraft:overworld"

        x_direction = Direction((1, 0))
        if not orientation.x:
            x_direction = -x_direction
        x_increment = x_direction[0]
        y_increment = 1
        if orientation.y:
            y_glass = Y + VOICE_HEIGHT * (composition.size + 1)
        else:
            y_increment = -y_increment
            y_glass = Y - 1
        z_direction = Direction((0, 1))
        if not orientation.z:
            z_direction = -z_direction
        z_increment = z_direction[1]

        Z_BOUNDARY = composition.division * NOTE_LENGTH + DIVISION_CHANGING_LENGTH + 2
        X_BOUNDARY = (composition.length + INIT_DIVISIONS) * DIVISION_WIDTH + 1
        Y_BOUNDARY = y_glass - VOICE_HEIGHT * (composition.size + 1)

        if len(composition) == 1:
            generate_orchestra(composition[0], z_direction)
            generate_init_system_for_single_orchestra()
        else:
            generate_orchestra(composition[0], z_direction)
            Z += z_increment * Z_BOUNDARY
            generate_orchestra(composition[1], z_direction)
            for i in range(composition.length // 2):
                generate_init_system_for_double_orchestras(2 * DIVISION_WIDTH * i)


def generate(path_out, **kwargs):
    with World(path_out) as world:
        world.generate(**kwargs)
