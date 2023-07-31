#!/usr/bin/env python
from __future__ import annotations

import json
import math
import sys
from enum import Enum

import amulet

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

# number of noteblocks to play the note,
# 0 for rest, upto 4 for loudest
DYNAMIC_RANGE = range(0, 5)


class UserError(Exception):
    pass


class Note:
    def __init__(
        self,
        _voice: Voice,
        name: str,
        delay: int = None,
        dynamic: int = None,
        instrument: str = None,
        transpose=0,
    ):
        self._name = name
        transpose = _voice.transpose + transpose
        if transpose > 0:
            self._name += f"+{transpose}"
        elif transpose < 0:
            self._name += f"{transpose}"

        if delay is None:
            delay = _voice.delay
        if delay < 1:
            raise UserError("delay must be >= 1.")
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
            pitch_value = PITCHES[name] + transpose
        except KeyError:
            raise UserError(f"{name} is not a valid note name.")
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
    def __init__(self, _voice: Voice, delay: int = None):
        if delay is None:
            delay = _voice.delay
        if delay < 1:
            raise UserError("delay must be >= 1.")
        self.delay = delay
        self.dynamic = 0
        self._name = "r"


class Voice(list[list[Note]]):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(
        self,
        _composition: Composition,
        notes: list[str | dict] = [],
        name: str = None,
        time: int = None,
        delay: int = None,
        beat: int = None,
        instrument: str = None,
        dynamic: int = None,
        transpose=0,
    ):
        if time is None:
            time = _composition.time
        if delay is None:
            delay = _composition.delay
        if beat is None:
            beat = _composition.beat
        if instrument is None:
            instrument = _composition.instrument
        if dynamic is None:
            dynamic = _composition.dynamic

        self._composition = _composition
        self._index = len(_composition)
        self._name = name
        self._config(
            time=time,
            delay=delay,
            beat=beat,
            instrument=instrument,
            dynamic=dynamic,
            transpose=transpose,
        )
        try:
            self._octave = (INSTRUMENTS[instrument].start - 6) // 12 + 2
        except KeyError:
            raise UserError(f"{self}: {instrument} is not a valid instrument.")
        if notes:
            self.append([])
            for note in notes:
                if len(self[-1]) == self.time:
                    self.append([])
                if isinstance(note, str):
                    kwargs = {"name": note}
                else:
                    kwargs = note
                if "name" in kwargs:
                    try:
                        self._add_note(kwargs.pop("name"), **kwargs)
                    except UserError as e:
                        at = (len(self), len(self[-1]) + 1)
                        raise UserError(f"{self} at {at}: {e}")
                else:
                    self._config(**kwargs)

    def __str__(self):
        if self._name:
            return self._name
        return f"Voice {self._index + 1}"

    def _config(
        self,
        time: int = None,
        delay: int = None,
        beat: int = None,
        instrument: str = None,
        dynamic: int = None,
        transpose: int = None,
    ):
        if time is not None:
            self.time = time
        if delay is not None:
            # delay of out range is handled by Note.__init__
            self.delay = delay
        if beat is not None:
            self.beat = beat
        if instrument is not None:
            # invalid instrument is handled by Note.__init__
            self.instrument = instrument
        if dynamic is not None:
            # dynamic out of range is handled by Note.__init__
            self.dynamic = dynamic
        if transpose is not None:
            self.transpose = self._composition.transpose + transpose

    def _rest(self, duration: int, *, delay: int = None, **kwargs) -> list[Note]:
        return [Rest(self, delay=delay)] * duration

    def _parse_pitch(self, name: str):
        if not name or name == "r":
            return "r"
        try:
            int(name[-1])
            return name
        except ValueError:
            if name.endswith("^"):
                return name[:-1] + str(self._octave + 1)
            elif name.endswith("_"):
                return name[:-1] + str(self._octave - 1)
            return name + str(self._octave)

    def _parse_duration(self, *args: str):
        if not args or not (value := args[0]):
            return self.beat
        if len(args) > 1:
            return self._parse_duration(args[0]) + self._parse_duration(*args[1:])
        try:
            if value[-1] == ".":
                return int(self._parse_duration(value[:-1]) * 1.5)
            if value[-1] == "b":
                return self.beat * int(value[:-1])
            else:
                return int(value)
        except ValueError:
            raise UserError(f"{value} is not a valid duration.")

    def _add_note(self, name: str, **kwargs):
        # parse note name into pitch + duration
        tokens = name.lower().split()
        # if note name is "||", fill the rest of the bar with rests
        if tokens[0].startswith("||"):
            self[-1] += self._rest(self.time - len(self[-1]))
            return
        # if "|", do a bar check (self-enforced linter)
        if tokens[0].startswith("|"):
            if self[-1]:
                raise UserError("time error.")
            return
        # we do ".startswith" rather than "=="
        # so that "|" or "||" can be followed by a numberc,
        # acting as the bar number, even though this number is not checked
        pitch = self._parse_pitch(tokens[0])
        duration = self._parse_duration(*tokens[1:])

        # divide note into actual note + rests
        if pitch == "r":
            notes = self._rest(duration, **kwargs)
        else:
            notes = [Note(self, pitch, **kwargs)] + self._rest(duration - 1, **kwargs)
        # organize those into barss
        for note in notes:
            if len(self[-1]) < self.time:
                self[-1].append(note)
            else:
                self.append([note])


class Composition(list[Voice]):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(
        self,
        voices: list[dict] = [],
        time=16,
        delay=1,
        beat=1,
        instrument="harp",
        dynamic=2,
        transpose=0,
    ):
        # values out of range are handled by Voice or Note __init__
        self.time = time
        self.delay = delay
        self.beat = beat
        self.name = name
        self.instrument = instrument
        self.dynamic = dynamic
        self.transpose = transpose

        for voice in voices:
            self.append(Voice(self, **voice))


class Block(amulet.api.block.Block):
    def __init__(self, name: str, **properties):
        properties = {k: amulet.StringTag(v) for k, v in properties.items()}
        super().__init__("minecraft", name, properties)


class NoteBlock(Block):
    def __init__(self, _note: Note):
        super().__init__("note_block", note=_note.note, instrument=_note.instrument)


class Direction(tuple[int, int], Enum):
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
        self._level.set_version_block(
            *coordinates, "minecraft:overworld", self.VERSION, block
        )


def generate(composition: Composition, path: str, location: tuple[float, float, float]):
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
                voice.insert(0, [Rest(voice, delay=1)] * composition.time)
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


def main(path_in: str, path_out: str, *location_args: str):
    with open(path_in, "r") as f:
        try:
            composition = Composition(**json.load(f))
        except UserError as e:
            print(e)
            sys.exit(1)

    generate(composition, path_out, tuple(map(int, location_args)))


if __name__ == "__main__":
    main(*sys.argv[1:])
