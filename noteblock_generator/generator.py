from __future__ import annotations

import math
import os
from enum import Enum
from functools import partial
from multiprocessing.pool import ThreadPool
from typing import Callable, Optional

import amulet

from .compiler import DYNAMIC_RANGE, Composition, Note, Rest, UserError, Voice
from .main import Location, Orientation

_Block = amulet.api.Block
_Level = amulet.api.level.World | amulet.api.level.Structure
_BlockPlacement = _Block | Callable[[tuple[int, int, int]], Optional[_Block]]


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

    # TODO: make this a command-line argument
    _VERSION = ("java", (1, 20))

    # only assigned values when __enter__ is called
    _level: _Level
    _generate_tasks: dict[tuple[int, int], dict[tuple[int, int, int], _BlockPlacement]]

    dimension = "minecraft:overworld"  # will be modified by self.generate()

    def __init__(self, path: str):
        self._path = str(path)
        self._block_translator_cache = {}
        self._chunk_cache = {}

    def __enter__(self):
        try:
            level = amulet.load_level(self._path)
        except Exception as e:
            raise UserError(
                f"Path {self._path} is invalid, or does not exist\n"
                f"{type(e).__name__}: {e}."
            )

        self._level = level
        self._modifications = {}
        self._translator = level.translation_manager.get_version(*self._VERSION).block
        self.players = list(map(level.get_player, level.all_player_ids()))
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._apply_modifications()
        self._level.save(progress_callback=partial(progress_bar, text="INFO - Saving"))
        self._level.close()

    def __getitem__(self, coordinates: tuple[int, int, int]):
        x, y, z = coordinates
        (cx, offset_x), (cz, offset_z) = divmod(x, 16), divmod(z, 16)
        chunk = self._get_chunk(cx, cz)
        base_block = chunk.get_block(offset_x, y, offset_z).base_block
        out, _, _ = self._translator.from_universal(base_block)
        return out

    def __setitem__(self, coordinates: tuple[int, int, int], block: _BlockPlacement):
        x, y, z = coordinates
        cx, cz = x // 16, z // 16
        if (cx, cz) not in self._modifications:
            self._modifications[cx, cz] = {}
        self._modifications[cx, cz][x, y, z] = block

    def _apply_modifications(self):
        def _apply(tasks: dict[tuple[int, int, int], _BlockPlacement]):
            for coordinates, placement in tasks.items():
                if callable(placement):
                    if (block := placement(coordinates)) is not None:
                        self._set_block(*coordinates, block)
                else:
                    self._set_block(*coordinates, placement)

        if not self._modifications:
            return

        tasks = self._modifications.values()
        total = len(tasks)
        with ThreadPool() as pool:
            for progress, _ in enumerate(pool.imap_unordered(_apply, tasks)):
                progress_bar(progress + 1, total, text="INFO - Generating")

    def _set_block(
        self,
        x: int,
        y: int,
        z: int,
        block: _Block,
    ):
        (cx, offset_x), (cz, offset_z) = divmod(x, 16), divmod(z, 16)
        chunk = self._get_chunk(cx, cz)
        universal_block = self._translate_block(block)
        chunk.set_block(offset_x, y, offset_z, universal_block)
        if (x, y, z) in chunk.block_entities:
            del chunk.block_entities[x, y, z]
        chunk.changed = True

    def _get_chunk(self, cx: int, cz: int):
        try:
            return self._chunk_cache[cx, cz]
        except KeyError:
            pass

        try:
            chunk = self._level.get_chunk(cx, cz, self.dimension)
        except amulet.api.errors.ChunkDoesNotExist:
            chunk = self._level.create_chunk(cx, cz, self.dimension)

        self._chunk_cache[cx, cz] = chunk
        return chunk

    def _translate_block(self, block: _Block, /):
        try:
            return self._block_translator_cache[block]
        except KeyError:
            pass

        universal_block, _, _ = self._translator.to_universal(block)
        self._block_translator_cache[block] = universal_block
        return universal_block

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
        def generate_init_system_for_single_orchestra(x0: int):
            button = Block("oak_button", face="floor", facing=-x_direction)
            redstone = Redstone(z_direction, -z_direction)

            x = X + x_increment * (x0 + math.ceil(DIVISION_WIDTH / 2))
            y = y_glass
            z = Z

            def first():
                def generate_button():
                    """A button in the middle of the structure."""
                    z_button = z + z_increment * math.ceil(Z_BOUNDARY / 2)
                    self[x, y, z_button] = block
                    self[x, y + 1, z_button] = button

                def generate_redstone_bridge():
                    """Connect the button to the main system."""
                    repeater = Repeater(delay=1, direction=-z_direction)

                    self[x, y - 3, z + z_increment] = block
                    self[x, y - 2, z + z_increment] = redstone
                    self[x, y - 1, z + z_increment] = air
                    self[x, y - 2, z + z_increment * 2] = block
                    self[x, y - 1, z + z_increment * 2] = redstone
                    self[x, y - 1, z + z_increment * 3] = block
                    self[x, y, z + z_increment * 3] = redstone

                    for i in range(4, math.ceil(Z_BOUNDARY / 2)):
                        self[x, y, z + z_increment * i] = block
                        self[x, y + 1, z + z_increment * i] = (
                            redstone if i % 16 else repeater
                        )

                def generate_empty_bridge():
                    """A bridge that leads to nowhere, just for symmetry."""
                    for i in range(math.ceil(Z_BOUNDARY / 2) + 1, Z_BOUNDARY - 3):
                        self[x, y, z + z_increment * i] = block

                generate_button()
                generate_redstone_bridge()
                generate_empty_bridge()

            def subsequent():
                self[x, y - 3, z + z_increment] = block
                self[x, y - 2, z + z_increment] = redstone
                self[x, y - 1, z + z_increment] = air
                self[x, y - 1, z + z_increment * 2] = redstone
                self[x, y - 1, z + z_increment * 3] = block

                self[x, y, z + z_increment * 2] = block
                self[x, y + 1, z + z_increment * 2] = button

            if x0 == 0:
                first()
            else:
                subsequent()

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

            x = X + x_increment * (x0 + math.ceil(DIVISION_WIDTH / 2))
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
                    "kelp",
                    "kelp_plant",
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
                optional_clear_range = range(y_glass - Y_BOUNDARY, y_glass)

                def remove_danger(xyz: tuple[int, int, int], /) -> Optional[_Block]:
                    if self[xyz].base_name in REMOVE_LIST:
                        return air

                for z in range(Z_BOUNDARY + 1):
                    for x in range(X_BOUNDARY + 1):
                        generate_walking_glass()
                        for y in optional_clear_range:
                            coordinates = (
                                X + x_increment * x,
                                y,
                                Z + z_increment * z,
                            )
                            if clear or x in (0, X_BOUNDARY) or z in (0, Z_BOUNDARY):
                                self[coordinates] = air
                            else:
                                self[coordinates] = remove_danger

            def generate_redstones():
                self[x, y, z] = block
                self[x, y + 1, z] = Repeater(note.delay, z_direction)
                self[x, y + 1, z + z_increment] = block
                self[x, y + 2, z + z_increment] = Redstone()
                self[x, y + 2, z + z_increment * 2] = block

            def generate_noteblocks():
                if not note.dynamic:
                    return

                placement_order = [
                    -x_increment,
                    x_increment,
                    -x_increment * 2,
                    x_increment * 2,
                ]

                noteblock = NoteBlock(note)
                for i in range(note.dynamic):
                    self[x + placement_order[i], y + 2, z + z_increment] = noteblock
                    if not clear:
                        self[x + placement_order[i], y + 1, z + z_increment] = air
                        self[x + placement_order[i], y + 3, z + z_increment] = air

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
            self.dimension = dimension
        else:
            try:
                self.dimension = self.players[0].dimension
            except IndexError:
                pass

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
        Y_BOUNDARY = VOICE_HEIGHT * (composition.size + 1)

        if len(composition) == 1:
            generate_orchestra(composition[0], z_direction)
            for i in range(composition.length // 2):
                generate_init_system_for_single_orchestra(2 * DIVISION_WIDTH * i)
        else:
            generate_orchestra(composition[0], z_direction)
            Z += z_increment * Z_BOUNDARY
            generate_orchestra(composition[1], z_direction)
            for i in range(composition.length // 2):
                generate_init_system_for_double_orchestras(2 * DIVISION_WIDTH * i)


def generate(path_out, **kwargs):
    with World(path_out) as world:
        progress_bar(0, 1, text="INFO - Generating")
        world.generate(**kwargs)


def progress_bar(iteration: float, total: float, *, text: str):
    percentage = f" {100*(iteration / total):.0f}% "
    margin = " " * (6 - len(percentage))

    terminal_width, _ = os.get_terminal_size()
    bar_length = max(0, terminal_width - (len(text) + 6) - 3)

    fill_length = int(bar_length * iteration // total)
    finished_portion = "#" * fill_length
    remaining_portion = "-" * (bar_length - fill_length)
    progress_bar = f"[{finished_portion}{remaining_portion}]" if bar_length else ""

    print(f"\r{text}{margin}{percentage}{progress_bar}", end="")

    if iteration == total:
        print()
