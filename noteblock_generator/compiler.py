from __future__ import annotations

import json
import logging
import math

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format="%(levelname)s - %(message)s")

# MAPPING OF PITCH NAMES TO NUMERICAL VALUE
_notes = ["c", "cs", "d", "ds", "e", "f", "fs", "g", "gs", "a", "as", "b"]
# create the first octave
_octaves = {1: {note: value for value, note in enumerate(_notes)}}
# extend accidentals
for name, value in dict(_octaves[1]).items():
    # sharps and double sharps
    _octaves[1][name + "s"] = value + 1
    # flats and double flats
    if not name.endswith("s"):
        _octaves[1][name + "b"] = value - 1
        _octaves[1][name + "bb"] = value - 2
# extend to octave 7
for i in range(1, 7):
    _octaves[i + 1] = {note: value + 12 for note, value in _octaves[i].items()}
# flatten octaves to pitches
PITCHES = {
    note + str(octave_number): value
    for octave_number, octave in _octaves.items()
    for note, value in octave.items()
}


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

    def __repr__(self):
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
        sustain: bool | int | str = None,
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
        self.bar = _composition.bar_length
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
                            f"{self} at {(self._bar_number, self._note_number)}: {e}"
                        )
                else:
                    self._note_config |= kwargs

    def __str__(self):
        if self._name:
            return self._name
        return f"Voice {self._index + 1}"

    @property
    def _bar_number(self):
        return math.ceil(len(self) / (self.time / self.bar))

    @property
    def _note_number(self):
        return 1 + len(self[-1]) + (0 if len(self) % 2 else self.bar)

    def _parse_note(self, value: str, beat: int = None):
        _tokens = value.lower().split()
        pitch = self._parse_pitch(_tokens[0])
        duration = self._parse_duration(*_tokens[1:], beat=beat)
        return pitch, duration

    def _parse_pitch(self, value: str):
        def _parse_note_and_octave(value: str) -> tuple[str, int]:
            try:
                octave = int(value[-1])
                return value[:-1], octave
            except ValueError:
                if value.endswith("^"):
                    note, octave = _parse_note_and_octave(value[:-1])
                    return note, octave + 1
                if value.endswith("_"):
                    note, octave = _parse_note_and_octave(value[:-1])
                    return note, octave - 1
                return value, self._octave

        if not value or value == "r":
            return "r"

        note, octave = _parse_note_and_octave(value)
        return note + str(octave)

    def _parse_duration(self, *values: str, beat: int = None) -> int:
        if beat is None:
            beat = self.beat

        if not values or not (value := values[0]):
            return beat

        if len(values) > 1:
            head = self._parse_duration(value, beat=beat)
            tails = self._parse_duration(*values[1:], beat=beat)
            return head + tails

        if value.startswith("-"):
            return -self._parse_duration(value[1:], beat=beat)

        try:
            if value[-1] == ".":
                return int(self._parse_duration(value[:-1], beat=beat) * 1.5)
            if value[-1] == "b":
                return beat * int(value[:-1])
            else:
                return int(value)
        except ValueError:
            raise UserError(f"{value} is not a valid duration.")

    def _Note(
        self,
        pitch: str,
        duration: int,
        *,
        sustain: bool | int | str = None,
        trill: str = None,
        **kwargs,
    ) -> list[Note]:
        if pitch == "r":
            return self._Rest(duration, **kwargs)

        note = Note(self, pitch=pitch, **kwargs)
        beat = kwargs["beat"] if "beat" in kwargs else None

        if sustain is None:
            sustain = self.sustain
        if sustain is True:
            sustain = duration
        elif sustain is False:
            sustain = 1
        elif not isinstance(sustain, int):
            sustain = self._parse_duration(*sustain.split(), beat=beat)
        if sustain < 0:
            sustain += duration
        if sustain < 1:
            sustain = 1
        if sustain > duration:
            raise UserError("Sustain duration cannot be longer than main note's.")

        if trill:
            trill_pitch, trill_duration = self._parse_note(trill, beat)
            if trill_duration < 0:
                trill_duration += duration
            if trill_duration < 0:
                raise UserError("Trill duration must be at least 1.")
            if trill_duration > duration:
                raise UserError("Trill duration cannot be longer than main note's.")
            alternating_notes = (note, Note(self, pitch=trill_pitch, **kwargs))
            out = [alternating_notes[i % 2] for i in range(trill_duration - 1)]
            out += self._Note(
                pitch=(pitch, trill_pitch)[(trill_duration - 1) % 2],
                duration=duration - trill_duration + 1,
                sustain=max(0, sustain - trill_duration) + 1,
                **kwargs,
            )
            return out

        sustain_dynamic = {"dynamic": max(min(1, note.dynamic), note.dynamic // 2)}
        return (
            [note]
            + [Note(self, pitch=pitch, **kwargs | sustain_dynamic)] * (sustain - 1)
            + self._Rest(duration - sustain, **kwargs)
        )

    def _Rest(self, duration: int, *, delay: int = None, **kwargs) -> list[Note]:
        return [Rest(self, delay=delay)] * duration

    def _add_note(self, *, name: str, beat: int = None, **kwargs):
        if len(self[-1]) == self.bar:
            self.append([])

        # Bar helpers
        # "|" to assert the beginning of a bar
        if name.startswith("|"):
            name = name[1:]
            if self._note_number != 1:
                raise UserError("Wrong barline location.")
            # "||" to assert the beginning of a bar AND rest for the entire bar
            if name.startswith("|"):
                name = name[1:]
                self._add_note(name=f"r {self.time}", **kwargs)
            # followed by a number to assert bar number
            if name.strip() and int(name) != (self._bar_number):
                raise UserError(f"expected bar {self._bar_number}, found {int(name)}.")
            return

        # actual note
        pitch, duration = self._parse_note(name, beat)
        if duration < 1:
            raise UserError("Note duration must be at least 1.")
        # organize into bars
        for note in self._Note(pitch, duration, **kwargs):
            if len(self[-1]) < self.bar:
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
        self.time = time
        for n in range(16, 4, -1):
            if time % n == 0:
                self.bar_length = n
                break
        else:
            logger.warn(f"time {time} is unusually large.")

        for voice in voices:
            self.append(Voice(self, **voice))

    @classmethod
    def compile(cls, path_in: str):
        with open(path_in, "r") as f:
            return cls(**json.load(f))
