#!/usr/bin/env python
from __future__ import annotations

import json
import math
import sys
from enum import Enum

import amulet

# ---------------------------------------- MAIN ----------------------------------------

"""Program usage: 
    generate.py [path to json file] [path to mc world] [(optional) build coordinates]
Example: "generate.py /home/user/my-song.json /home/user/minecraft/saves/My-World 0 0 0"
If build coordinates are not provided, it will be the player's location.

See the TRANSLATOR section for how to write the json file.
See the GENERATOR section for what the generated structure will look like.
"""


def main(path_in: str, path_out: str, *location: str):
    with open(path_in, "r") as f:
        try:
            composition = Composition(**json.load(f))
        except UserError as e:
            print(e)
            sys.exit(1)

    generate(composition, path_out, tuple(map(int, location)))


# ------------------------------------- TRANSLATOR -------------------------------------

"""The json file should be in this format:
{
    // Composition

    // optional arguments

    "time": [how many steps in a bar],
    // If the time signature is 3/4, and we want to be able to play 16th notes,
    // the number of steps in a bar is 12.
    // Default value is 16, that is, 4/4 time and the ability to play 16th notes.
    // See GENERATOR section for how this value affects the build.

    "delay": [how many redstone ticks between each step],
    // Must be from 1 to 4, default value is 1.
    // For reference, if time is 16 and delay is 1, 
    // it is equivalent to the tempo "quarter note = 150 bpm"

    "beat": [how many steps in a beat],
    // Does not affect the build, but is useful for writing notes (explained later).
    // Default value is 1.

    "instrument": "[noteblock instrument to play the notes]",
    // Default value is "harp".
    // See minecraft's documentations for all available instruments.

    "dynamic": [how many noteblocks to play the note],
    // Must be from 0 to 4, where 0 is silent and 4 is loudest.
    // Default value is 2.

    "transpose": [transpose the entire composition, in semitones],
    // Default value is 0.

    // Mandatory argument
    "voices": // an array of voices
    [
        {
            // Voice 1

            // Optional arguments

            "name": "[voice name]",
            // Does not affect the build, but is useful for error messages, which, if
            // voice name is given, will tell you at which voice you've made an error,
            // e.g. invalid note name, note out of range for instrument, etc.

            "transpose": [transpose this particular voice, in semitones],
            // This value is compounded with the composition's transposition.
            // Default value is 0

            "time": [override the composition's time value],
            "delay": [override the composition's delay value],
            "beat": [override the composition's beat value],
            "instrument": "[override the composition's instrument value]"
            "dynamic": [override the composition's dynamic value]
            // some instruments are inherently louder than others,
            // it is recommened to adjust dynamic level of every voice
            // to compensate for this fact.
            
            // Mandatory argument
            "notes":  // an array of notes
            [
                // There are two ways to write notes.
                // First is as a json object, like this

                {
                    // Note 1

                    // Optional arguments

                    "transpose": [transpose this particular note, in semitones],
                    // This value is compounded with the voice's transposition.
                    // Default value: 0
        
                    "delay": [override the voice's delay value],
                    "dynamic": [override the voice's dynamic value],
                    "instrument": "[override the voice's instrument value]",

                    // (sort-of) Mandatory argument
                    "name": "[note name][octave] [duration 1] [duration 2] [etc.]"

                    // Valid note names are "r" (for rest) and "c", "cs", "db", etc.
                    // where "s" is for sharp and "b" is for flat.
                    // Double sharps, double flats are supported.

                    // Octaves are from 1 to 7. Note, however, that the lowest pitch 
                    // noteblocks can play is F#1 and the highest is F#7,
                    // so just because you can write it doesn't mean it will build
                    // (but you can transpose it to fit the range).
                    // Octave number can be inferred from the instrument's range.
                    // For example, the harp's range is F#3 - F#5, so
                    // "fs" is inferred as F#4, "fs^" as F#5, and "fs_" as F#3.
                    // See minecraft's documentation for the range of each instrument.

                    // Duration is the number of steps.
                    // If duration is omitted, it will be the beat number.
                    // If multiple durations are given, they will be summed up,
                    // for example, note name "cs4 1 2 3" is the same as "cs4 6",
                    // which is C#4 for 6 steps.
                    // Because noteblocks cannot sustain, a note with duration n
                    // is the same as the note with duration 1 and n-1 rests. 
                    // However it is recommended to write notes as they are written 
                    // in the score for readability.

                    // The note name "||" is short for 
                    "rest for the remaining of the current bar."

                    // If a note object does not have the "name" value, the other key-
                    // -value pairs will be applied all subsequent notes in its voice.
                    // If a subsequent note defines its own values, some of which
                    // overlap with these values, the note's values take precedence.
                },

                {
                    // Note 2
                    // etc.
                },

                // Note 3, etc.

                // Another way is to write it as a string, which is the same as
                // { "name": "that string" }

                // Bar changes are handled automatically based on the voice's time;
                // however, the recommended practice is to write a pseudo-note 
                // "| [bar number]" at the beginning of every bar. 
                // The "|" symbol tells the translator to check if it's 
                indeed the beginning of a bar, and raise an error if it isn't.
                // Meanwhile, the bar number is just for your own reference.
            ]
        },
        
        {
            // Voice 2
            // etc.
        },
        
        // Voice 3, etc.
    ]
}
"""

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
        /,
        *,
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
        /,
        *,
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
        /,
        *,
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
            notes = [Note(self, name=pitch, **kwargs)] + self._rest(
                duration - 1, **kwargs
            )
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
        /,
        *,
        voices: list[dict] = [],
        time=16,
        delay=1,
        beat=1,
        instrument="harp",
        dynamic=2,
        transpose=0,
    ):
        # values out of range are handled by Voice/Note.__init__
        self.time = time
        self.delay = delay
        self.beat = beat
        self.name = name
        self.instrument = instrument
        self.dynamic = dynamic
        self.transpose = transpose

        for voice in voices:
            self.append(Voice(self, **voice))


# ------------------------------------- GENERATOR -------------------------------------

"""The structure of one voice looks something like this

x
↑ 
| [BAR 5] etc.
|          ↑
|          -- note <- note <- note [BAR 4]
|                               ↑
| [BAR 3] note -> note -> note --
|          ↑
|          -- note <- note <- note [BAR 2]
|                               ↑
| [BAR 1] note -> note -> note --
|
O--------------------------------------> z

and each voice is a vertical layer on top of another.
Voices are built in the order that they are written in the json file,
from bottom to top.
For this reason it is recommended to give lower voices higher dynamic levels,
to compensate for the fact that being further away from the player who flies above
they are harder to hear.

The "O" of the first voice is considered the location of the build.
The build coordinates mentioned in MAIN section are the coordinates of this location.

Each "note" in the above diagram is a group that looks something like this

x
↑
|           [noteblock]
|           [noteblock]
| [repeater]  [stone] 
|           [noteblock]
|           [noteblock]
|
|-----------------------> z

The number of noteblocks depends on the note's dynamic level,
this diagram shows one with maximum dynamic level 4.

Upon being called, the generator fills the required space start from the build location
with air, then generates the structure.
"""


class Block(amulet.api.block.Block):
    """A thin wrapper of amulet block, with a more convenient constructor"""

    def __init__(self, name: str, **properties):
        properties = {k: amulet.StringTag(v) for k, v in properties.items()}
        super().__init__("minecraft", name, properties)


class NoteBlock(Block):
    """A cnvenience class for noteblocks"""

    def __init__(self, _note: Note):
        super().__init__("note_block", note=_note.note, instrument=_note.instrument)


class Direction(tuple[int, int], Enum):
    """Minecraft's cardinal direction"""

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
    """A convenience class for redstone dusts"""

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


if __name__ == "__main__":
    main(*sys.argv[1:])
