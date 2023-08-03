#!/usr/bin/env python
from __future__ import annotations

import json
import math
import sys
from enum import Enum

import amulet

# ------------------------------------- TRANSLATOR -------------------------------------

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


# The following classes -- Note, Voice, Composition -- are
# almost 1-1 translation of the json file in python's format.


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
                        print(f"{self} at {(len(self), len(self[-1]) + 1)}: {e}")
                        sys.exit(1)
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


# ------------------------------------- GENERATOR -------------------------------------


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
        if self == Direction.north:
            return Direction.south
        if self == Direction.south:
            return Direction.north
        if self == Direction.east:
            return Direction.west
        return Direction.east

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
    with __setitem__ as a convenience method for World.set_version_block,
    and a context manager to load and save.
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


def generate(composition: Composition, path: str, location: tuple[float, float, float]):
    def equalize_voices():
        for voice in composition:
            if (L := len(voice)) < LONGEST_VOICE:
                voice += [[Rest(voice)] * voice.time] * (LONGEST_VOICE - L)

    def generate_space():
        notes = composition.time
        bars = LONGEST_VOICE + INIT_BARS
        voices = len(composition)
        for z in range(notes * NOTE_LENGTH + BAR_CHANGING_TOTAL_LENGTH + 2 * MARGIN):
            for x in range(bars * BAR_WIDTH + 2 * MARGIN):
                world[X0 + x, Y0, Z0 + z] = Stone
                for y in range(1, voices * VOICE_HEIGHT + 2 * MARGIN):
                    world[X0 + x, Y0 + y, Z0 + z] = Air

    def generate_init_system():
        for voice in composition:
            for _ in range(INIT_BARS):
                voice.insert(0, [Rest(voice, delay=1)] * voice.time)
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
    BAR_WIDTH = DYNAMIC_RANGE.stop  # 4 noteblocks, 2 each side + 1 stone in the middle
    VOICE_HEIGHT = 2
    BAR_CHANGING_LENGTH = 2  # how many blocks it takes to wrap around and change bar
    BAR_CHANGING_TOTAL_LENGTH = BAR_CHANGING_LENGTH + 1  # 1 for z-offset every change
    LONGEST_VOICE = max(map(len, composition))
    # add this number of bars to the beginning of every voice
    # so that with a push of a button, all voices start at the same time
    INIT_BARS = math.ceil((len(composition) - 1) / composition.time)

    with World(path) as world:
        Stone = Block("stone")
        Air = Block("air")

        x_direction = Direction((1, 0))
        if not location:
            try:
                location = world.players[0].location
            except IndexError:
                location = (0, 0, 0)
        X0, Y0, Z0 = map(math.floor, location)

        equalize_voices()
        generate_space()
        generate_init_system()

        for i, voice in enumerate(composition):
            y = Y0 + MARGIN + i * VOICE_HEIGHT
            z = Z0 + MARGIN + BAR_CHANGING_TOTAL_LENGTH
            z_direction = Direction((0, 1))

            for j, bar in enumerate(voice):
                x = X0 + MARGIN + BAR_WIDTH // 2 + j * BAR_WIDTH
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


# ---------------------------------------- MAIN ----------------------------------------


def main(path_in: str, path_out: str, *location: str):
    with open(path_in, "r") as f:
        generate(Composition(**json.load(f)), path_out, tuple(map(int, location)))


if __name__ == "__main__":
    main(*sys.argv[1:])
