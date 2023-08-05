#!/usr/bin/env python
from __future__ import annotations

import json
import logging
import math
import sys
from argparse import ArgumentParser
from enum import Enum
from typing import NamedTuple

logging.basicConfig(level=logging.WARNING)
import amulet  # noqa: E402

# ===================================== TRANSLATOR =====================================

# MAPPING OF PITCH NAMES TO NUMERICAL VALUES
# create first octave
_first = ["c1", "cs1", "d1", "ds1", "e1", "f1", "fs1", "g1", "gs1", "a1", "as1", "b1"]
_octaves = [_first]
# dynamically extend to octave 7
for _ in range(6):
    _octaves.append([p[:-1] + str(int(p[-1]) + 1) for p in _octaves[-1]])
# flatten and convert to dict
PITCHES = {
    name: value
    for value, name in enumerate([pitch for octave in _octaves for pitch in octave])
}
# extend accidentals
for name, value in dict(PITCHES).items():
    if name[-2] == "s":
        # double sharps
        if value + 1 < 84:
            PITCHES[name[:-1] + "s" + name[-1]] = value + 1
            PITCHES[name[:-2] + "x" + name[-1]] = value + 1
    else:
        # sharps
        if value + 1 < 84:
            PITCHES[name[:-1] + "s" + name[-1]] = value + 1
        # flats
        if value - 1 >= 0:
            PITCHES[name[:-1] + "b" + name[-1]] = value - 1
        # double flats
        if value - 2 >= 0:
            PITCHES[name[:-1] + "bb" + name[-1]] = value - 2

# MAPPING OF INSTRUMENTS TO NUMERICAL RANGES
INSTRUMENTS = {
    "bass": range(6, 31),
    "didgeridoo": range(6, 31),
    "guitar": range(18, 43),
    "harp": range(30, 55),
    "bit": range(30, 55),
    "banjo": range(30, 55),
    "iron_xylophone": range(30, 55),
    "pling": range(30, 55),
    "flute": range(42, 67),
    "cow_bell": range(42, 67),
    "bell": range(54, 79),
    "xylophone": range(54, 79),
    "chime": range(54, 79),
    "basedrum": range(6, 31),
    "hat": range(42, 67),
    "snare": range(42, 67),
}

DELAY_RANGE = range(1, 5)
DYNAMIC_RANGE = range(0, 5)


class UserError(Exception):
    """To be raised if there is an error when translating the json file,
    e.g. invalid instrument name or note out of the instrument's range.
    """


class Note:
    def __init__(
        self,
        _voice: Voice,
        *,
        pitch: str,
        delay: int = None,
        dynamic: int = None,
        instrument: str = None,
        transpose=0,
    ):
        self._name = pitch
        transpose = _voice.transpose + transpose
        if transpose > 0:
            self._name += f"+{transpose}"
        elif transpose < 0:
            self._name += f"{transpose}"

        if delay is None:
            delay = _voice.delay
        if delay not in DELAY_RANGE:
            raise UserError(f"delay must be in {DELAY_RANGE}.")
        self.delay = delay

        if instrument is None:
            instrument = _voice.instrument
        self.instrument = instrument

        if dynamic is None:
            dynamic = _voice.dynamic
        if dynamic not in DYNAMIC_RANGE:
            raise UserError(f"dynamic must be in {DYNAMIC_RANGE}.")
        self.dynamic = dynamic

        try:
            pitch_value = PITCHES[pitch] + transpose
        except KeyError:
            raise UserError(f"{pitch} is not a valid note name.")
        try:
            instrument_range = INSTRUMENTS[instrument]
        except KeyError:
            raise UserError(f"{instrument} is not a valid instrument.")
        if pitch_value not in instrument_range:
            raise UserError(f"{self} is out of range for {instrument}.")
        self.note = instrument_range.index(pitch_value)

    def __str__(self):
        return self._name


class Rest(Note):
    def __init__(self, _voice: Voice, /, *, delay: int = None):
        if delay is None:
            delay = _voice.delay
        if delay not in DELAY_RANGE:
            raise UserError(f"delay must be in {DELAY_RANGE}.")
        self.delay = delay
        self.dynamic = 0
        self._name = "r"


class Voice(list[list[Note]]):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(
        self,
        _composition: Composition,
        *,
        notes: list[str | dict],
        name: str = None,
        delay: int = None,
        beat: int = None,
        instrument: str = None,
        dynamic: int = None,
        transpose=0,
        sustain: bool = None,
    ):
        if delay is None:
            delay = _composition.delay
        if beat is None:
            beat = _composition.beat
        if instrument is None:
            instrument = _composition.instrument
        if dynamic is None:
            dynamic = _composition.dynamic
        if sustain is None:
            sustain = _composition.sustain
        try:
            self._octave = (INSTRUMENTS[instrument].start - 6) // 12 + 2
        except KeyError:
            raise UserError(f"{self}: {instrument} is not a valid instrument.")
        self._composition = _composition
        self._index = len(_composition)
        self._name = name
        self.time = _composition.time
        self.delay = delay
        self.beat = beat
        self.instrument = instrument
        self.dynamic = dynamic
        self.transpose = _composition.transpose + transpose
        self.sustain = sustain

        if notes:
            self._note_config = {}
            self.append([])
            for note in notes:
                if len(self[-1]) == self.time:
                    self.append([])
                kwargs = note if isinstance(note, dict) else {"name": note}
                if "name" in kwargs:
                    try:
                        self._add_note(**(self._note_config | kwargs))
                    except UserError as e:
                        raise UserError(
                            f"{self} at {(len(self), len(self[-1]) + 1)}: {e}",
                        )
                else:
                    self._note_config |= kwargs

    def __str__(self):
        if self._name:
            return self._name
        return f"Voice {self._index + 1}"

    def _parse_pitch(self, value: str):
        if not value or value == "r":
            return "r"
        try:
            int(value[-1])
            return value
        except ValueError:
            if value.endswith("^"):
                return value[:-1] + str(self._octave + 1)
            elif value.endswith("_"):
                return value[:-1] + str(self._octave - 1)
            return value + str(self._octave)

    def _parse_duration(self, beat: int = None, *values: str):
        if beat is None:
            beat = self.beat

        if not values or not (value := values[0]):
            return beat

        if len(values) > 1:
            head = self._parse_duration(beat, values[0])
            tails = self._parse_duration(beat, *values[1:])
            return head + tails
        try:
            if value[-1] == ".":
                return int(self._parse_duration(beat, value[:-1]) * 1.5)
            if value[-1] == "b":
                return beat * int(value[:-1])
            else:
                return int(value)
        except ValueError:
            raise UserError(f"{value} is not a valid duration.")

    def _Note(
        self, pitch: str, duration: int, *, sustain: bool = None, **kwargs
    ) -> list[Note]:
        if pitch == "r":
            return self._Rest(duration, **kwargs)
        note = Note(self, pitch=pitch, **kwargs)
        if sustain is None:
            sustain = self.sustain
        if sustain:
            return [note] * duration
        return [note] + self._Rest(duration - 1, **kwargs)

    def _Rest(self, duration: int, *, delay: int = None, **kwargs) -> list[Note]:
        return [Rest(self, delay=delay)] * duration

    def _add_note(self, *, name: str, beat: int = None, **kwargs):
        # Bar helpers
        # "|" to assert the beginning of a bar
        if name.startswith("|"):
            name = name[1:]
            if self[-1]:
                raise UserError("expected the beginning of a bar.")
            # "||" to assert the beginning of a bar AND rest for the entire bar
            if name.startswith("|"):
                name = name[1:]
                self[-1] += self._Rest(self.time, **kwargs)
            # followed by a number to assert bar number
            if name.strip() and int(name) != len(self):
                raise UserError(f"expected bar {len(self)}, found {int(name)}.")
            return

        # actual note
        tokens = name.lower().split()
        pitch = self._parse_pitch(tokens[0])
        duration = self._parse_duration(beat, *tokens[1:])
        # organize into bars
        for note in self._Note(pitch, duration, **kwargs):
            if len(self[-1]) < self.time:
                self[-1].append(note)
            else:
                self.append([note])


class Composition(list[Voice]):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(
        self,
        *,
        voices: list[dict],
        time=16,
        delay=1,
        beat=1,
        instrument="harp",
        dynamic=2,
        transpose=0,
        sustain=False,
    ):
        # values out of range are handled by Voice/Note.__init__
        self.time = time
        self.delay = delay
        self.beat = beat
        self.name = name
        self.instrument = instrument
        self.dynamic = dynamic
        self.transpose = transpose
        self.sustain = sustain

        for voice in voices:
            self.append(Voice(self, **voice))


def translate(json_path: str) -> Composition:
    with open(json_path, "r") as f:
        return Composition(**json.load(f))


# ===================================== GENERATOR =====================================


class Block(amulet.api.block.Block):
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

    def __init__(
        self,
        connections=list(Direction),  # connected to all sides by default
    ):
        # only support connecting sideways,
        # because that's all we need for this build
        super().__init__(
            "redstone_wire",
            **{direction.name: "side" for direction in connections},
        )


class World:
    """A thin wrapper of amulet World,
    with convenient methods to load, set blocks, and save.
    """

    # to be updated in the future
    # as for now, this works for java 1.18+
    VERSION = ("java", (1, 20))

    def __init__(self, path: str):
        self._path = str(path)

    def __enter__(self):
        self._level = (level := amulet.load_level(self._path))
        self.players = list(map(level.get_player, level.all_player_ids()))
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is None and self._level.changed:
            self._level.save()
        self._level.close()

    def __setitem__(self, coordinates: tuple[int, int, int], block: Block):
        # only support placing blocks in the overworld,
        # because that's all we need for this build
        self._level.set_version_block(
            *coordinates, "minecraft:overworld", self.VERSION, block
        )


def generate(
    composition: Composition,
    world: World,
    *,
    location: Location,
    orientatation: Orientation,
    block: str,
    clear=False,
):
    def generate_space():
        air = Block("air")
        glass = Block("glass")

        notes = composition.time
        bars = LONGEST_VOICE_LENGTH + INIT_BARS
        voices = len(composition)

        if orientatation.y:
            y = Y0 + VOICE_HEIGHT * (len(composition) + 1)
        else:
            y = Y0 - MARGIN

        for z in range(notes * NOTE_LENGTH + BAR_CHANGING_LENGTH + 1 + 2 * MARGIN):
            for x in range(bars * BAR_WIDTH + 2 * MARGIN):
                if orientatation.y:
                    y = Y0 + voices * VOICE_HEIGHT + 2 * MARGIN
                    clear_range = range(0, y - Y0)
                else:
                    y = Y0 - MARGIN
                    clear_range = range(2 * MARGIN, VOICE_HEIGHT * voices)

                world[X0 + x_increment * x, y, Z0 + z_increment * z] = glass

                if clear:
                    for y in clear_range:
                        world[
                            X0 + x_increment * x,
                            Y0 + y_increment * y,
                            Z0 + z_increment * z,
                        ] = air

    def generate_init_system():
        for voice in composition:
            for _ in range(INIT_BARS):
                voice.insert(0, [Rest(voice, delay=1)] * voice.time)

        x = X0 + x_increment * (MARGIN + BAR_WIDTH // 2)
        if orientatation.y:
            y = Y0 + VOICE_HEIGHT * (len(composition) + 1)
        else:
            y = Y0 - MARGIN
        z = Z0 + z_increment * BAR_CHANGING_LENGTH
        world[x, y - 1, z] = Redstone()
        world[x, y, z] = neutral_block
        world[x, y + 1, z] = Block("oak_button", face="floor", facing=-x_direction)

    def generate_redstones():
        world[x, y, z] = neutral_block
        world[x, y + 1, z] = Repeater(note.delay, z_direction)
        world[x, y + 1, z + z_increment] = neutral_block
        world[x, y + 2, z + z_increment] = Redstone()
        world[x, y + 2, z + z_increment * 2] = neutral_block

    def generate_noteblocks():
        # place noteblock positions in this order, depending on dynamic
        positions = [1, -1, 2, -2]
        for i in range(note.dynamic):
            world[x + positions[i], y + 2, z + z_increment] = NoteBlock(note)

    def generate_bar_changing_system():
        world[x, y, z + z_increment * 2] = neutral_block
        world[x, y + 1, z + z_increment * 2] = Redstone((z_direction, -z_direction))
        world[x, y, z + z_increment * 3] = neutral_block
        world[x, y + 1, z + z_increment * 3] = Redstone((x_direction, -z_direction))
        for i in range(1, BAR_WIDTH):
            world[x + x_increment * i, y, z + z_increment * 3] = neutral_block
            world[x + x_increment * i, y + 1, z + z_increment * 3] = Redstone(
                (x_direction, -x_direction)
            )
        world[x + x_increment * BAR_WIDTH, y, z + z_increment * 3] = neutral_block
        world[x + x_increment * BAR_WIDTH, y + 1, z + z_increment * 3] = Redstone(
            (-z_direction, -x_direction)
        )

    if not composition:
        return

    MARGIN = 1
    NOTE_LENGTH = 2
    BAR_WIDTH = DYNAMIC_RANGE.stop  # 4 noteblocks + 1 stone in the middle
    VOICE_HEIGHT = 2
    BAR_CHANGING_LENGTH = 2  # how many blocks it takes to wrap around and change bar
    LONGEST_VOICE_LENGTH = max(map(len, composition))
    # add this number of bars to the beginning of every voice
    # so that with a push of a button, all voices start at the same time
    INIT_BARS = math.ceil((len(composition) - 1) / composition.time)

    try:
        player_location = tuple(map(math.floor, world.players[0].location))
    except IndexError:
        player_location = (0, 0, 0)
    X0, Y0, Z0 = location
    if location.x.relative:
        X0 += player_location[0]
    if location.y.relative:
        Y0 += player_location[1]
    if location.z.relative:
        Z0 += player_location[2]

    x_direction = Direction((1, 0))
    if not orientatation.x:
        x_direction = -x_direction
    x_increment = x_direction[0]
    y_increment = 1
    if not orientatation.y:
        y_increment = -y_increment
    z_direction = Direction((0, 1))
    if not orientatation.z:
        z_direction = -z_direction
    z_increment = z_direction[1]

    neutral_block = Block(block)

    generate_space()
    generate_init_system()

    for i, voice in enumerate(composition):
        y = Y0 + y_increment * i * VOICE_HEIGHT
        if not orientatation.y:
            y -= VOICE_HEIGHT + 3 * MARGIN
        z = Z0 + z_increment * (MARGIN + BAR_CHANGING_LENGTH + 1)

        for j, bar in enumerate(voice):
            x = X0 + x_increment * (MARGIN + BAR_WIDTH // 2 + j * BAR_WIDTH)
            z_increment = z_direction[1]
            z0 = z - z_increment * BAR_CHANGING_LENGTH
            world[x, y + 2, z0] = neutral_block

            for k, note in enumerate(bar):
                z = z0 + k * z_increment * NOTE_LENGTH
                generate_redstones()
                generate_noteblocks()

            # if there is a next bar, change bar
            try:
                voice[j + 1]
            except IndexError:
                pass
            else:
                generate_bar_changing_system()
                z_direction = -z_direction

        # if number of bar is even
        if len(voice) % 2 == 0:
            # z_direction has been flipped, reset it to original
            z_direction = -z_direction
            z_increment = z_direction[1]


# ======================================== MAIN ========================================


class Arguments(NamedTuple):
    path_in: str
    path_out: str
    location: Location
    orientation: Orientation
    block: str
    clear: bool


def get_args():
    parser = ArgumentParser(
        description="Noteblock music generator",
    )
    parser.add_argument("path_in", help="path to music json file.")
    parser.add_argument("path_out", help="path to Minecraft world.")
    parser.add_argument(
        "-l",
        "--location",
        nargs="*",
        default=["~", "~", "~"],
        help="coordinates to generate location; default is ~ ~ ~ (player's location)",
    )
    parser.add_argument(
        "-o",
        "--orientation",
        nargs="*",
        default=["+", "+", "+"],
        help=(
            "in which directions (with respect to x y z) to generate; "
            "default is + + +"
        ),
    )
    parser.add_argument(
        "-b",
        "--block",
        default="stone",
        help="what to use as opaque blocks for redstone components; default is stone",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help=(
            "clear the space before generating; "
            "required to generate in a non-empty world but will take more time"
        ),
    )
    return parser.parse_args(args=None if sys.argv[1:] else ["--help"])


class Coordinate(int):
    relative: bool

    def __new__(cls, value: int, relative=False):
        self = super().__new__(cls, value)
        self.relative = relative
        return self


class Location(NamedTuple):
    x: Coordinate
    y: Coordinate
    z: Coordinate


class Orientation(NamedTuple):
    x: bool
    y: bool
    z: bool


def parse_args():
    args = get_args()

    if len(args.location) != 3:
        raise UserError("3 coordinates are required.")
    location: list[Coordinate] = []
    for arg in args.location:
        if relative := arg.startswith("~"):
            arg = arg[1:]
        if not arg:
            value = 0
        else:
            try:
                value = int(arg)
            except ValueError:
                raise UserError(f"Expected integer coordinates; found {arg}.")
        location.append(Coordinate(value, relative=relative))

    if len(args.orientation) != 3:
        raise UserError("3 orientations are required.")
    orientation: list[bool] = []
    _options = "+-"
    for arg in args.orientation:
        try:
            orientation.append(_options.index(arg) == 0)
        except ValueError:
            raise UserError(f"{arg} is not a valid direction; expected + or -.")

    return Arguments(
        args.path_in,
        args.path_out,
        Location(*location),
        Orientation(*orientation),
        args.block,
        args.clear,
    )


def main():
    try:
        args = parse_args()
        composition = translate(args.path_in)
    except UserError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    with World(args.path_out) as world:
        generate(
            composition,
            world,
            location=args.location,
            orientatation=args.orientation,
            block=args.block,
            clear=args.clear,
        )


if __name__ == "__main__":
    main()
