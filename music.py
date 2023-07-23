from __future__ import annotations

import math


class UNREACHABLE(Exception):
    """For comment and debugging"""


# MAPPING OF PITCH NAMES TO NUMERICAL VALUES
# create first octave
_first = ["c1", "cs1", "d1", "ds1", "e1", "f1", "fs1", "g1", "gs1", "a1", "as1", "b1"]
_octaves = [_first]
# dynamically extend to octave 7
for _ in range(6):
    _octaves.append([p[:-1] + str(int(p[-1]) + 1) for p in _octaves[-1]])
# flatten and convert to dict
ORIGINAL_PITCHES = {
    name: value
    for value, name in enumerate([pitch for octave in _octaves for pitch in octave])
}
# extend accidentals
PITCHES = dict(ORIGINAL_PITCHES)
for name, value in ORIGINAL_PITCHES.items():
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
    "basedrum": range(79),
    "hat": range(79),
    "snare": range(79),
    None: range(79),
}


class Composition:
    def __init__(
        self,
        time: int,
        tempo: int,
        voices: list[dict],
        name: str = None,
        instrument: str = None,
        dynamic=2,
        transpose=0,
        autoReplaceOctaveEquivalent=False,
    ):
        self.time = time
        self.tempo = tempo
        self.name = name
        self.instrument = instrument
        self.dynamic = dynamic
        self.transpose = transpose
        self.autoReplaceOctaveEquivalent = autoReplaceOctaveEquivalent
        self._voices = [Voice(self, **voice) for voice in voices]

    def __iter__(self):
        yield from self._voices

    def __str__(self):
        if self.name is not None:
            return self.name
        return super().__str__()


class Voice:
    def __init__(
        self,
        _composition: Composition,
        notes: list[str | dict],
        name: str = None,
        time: int = None,
        tempo: int = None,
        instrument: str = None,
        dynamic: int = None,
        transpose: int = None,
        autoReplaceOctaveEquivalent: bool = None,
    ):
        self.name = name
        if time is None:
            time = _composition.time
        if tempo is None:
            tempo = _composition.tempo
        if instrument is None:
            instrument = _composition.instrument
        if dynamic is None:
            dynamic = _composition.dynamic
        if transpose is None:
            transpose = _composition.transpose
        if autoReplaceOctaveEquivalent is None:
            autoReplaceOctaveEquivalent = _composition.autoReplaceOctaveEquivalent

        self.name = name
        self._config(
            time, tempo, instrument, dynamic, transpose, autoReplaceOctaveEquivalent
        )

        self._bars: list[Bar] = [Bar()]
        for note in notes:
            if isinstance(note, str):
                note = {"name": note}
            self._add_note(**note)

    @property
    def current_position(self):
        """For error message"""
        return (len(self._bars), len(self._bars[-1]) + 1)

    def __iter__(self):
        yield from self._bars

    def __str__(self):
        if self.name:
            return self.name
        if self._bars:
            if first_bar := self._bars[0]:
                if instrument := first_bar[0].instrument:
                    return instrument
        return super().__str__()

    def _config(
        self,
        time: int = None,
        tempo: int = None,
        instrument: str = None,
        dynamic: int = None,
        transpose: int = None,
        autoReplaceOctaveEquivalent: bool = None,
    ):
        if time is not None:
            self.time = time
        if tempo is not None:
            self.tempo = tempo
        if instrument is not None:
            self.instrument = instrument
        if dynamic is not None:
            self.dynamic = dynamic
        if transpose is not None:
            self.transpose = transpose
        if autoReplaceOctaveEquivalent is not None:
            self.autoReplaceOctaveEquivalent = autoReplaceOctaveEquivalent

    def _rest(self, duration: int) -> list[Note]:
        return [Rest(self)] * duration

    def _add_note(self, **kwargs):
        if "name" in kwargs:
            # parse note name
            pitch, _duration = kwargs.pop("name").lower().split(maxsplit=1)
            duration = int(_duration)
            if pitch == "r":
                notes = self._rest(duration)
            else:
                notes = [Note(self, pitch, **kwargs)] + self._rest(duration - 1)

            # organize into bars
            for note in notes:
                if (L := len(self._bars[-1])) < self.time:
                    self._bars[-1].append(note)
                elif L == self.time:
                    self._bars.append(Bar([note]))
                else:
                    raise ValueError(f"{self} at {self.current_position}: time error.")
            if len(self._bars[-1]) == self.time:
                self._bars.append(Bar())
        else:
            self._config(**kwargs)


class Note:
    def __init__(
        self,
        _voice: Voice,
        name: str,
        tempo: int = None,
        instrument: str = None,
        dynamic: int = None,
        transpose: int = None,
        autoReplaceOctaveEquivalent: bool = None,
    ):
        if tempo is None:
            tempo = _voice.tempo
        if instrument is None:
            instrument = _voice.instrument
        if dynamic is None:
            dynamic = _voice.dynamic
        if transpose is None:
            transpose = _voice.transpose
        if autoReplaceOctaveEquivalent is None:
            autoReplaceOctaveEquivalent = _voice.autoReplaceOctaveEquivalent

        self.name = name
        if transpose > 0:
            self.name += f"+{transpose}"
        elif transpose < 0:
            self.name += f"{transpose}"
        self.delay = tempo
        self.instrument = instrument
        self.dynamic = dynamic

        pitch_value = PITCHES[name] + transpose
        try:
            instrument_range = INSTRUMENTS[instrument]
        except KeyError:
            raise KeyError(f"{_voice}: invalid instrument.")
        if pitch_value not in instrument_range:
            if not autoReplaceOctaveEquivalent:
                raise ValueError(
                    f"{_voice} at {_voice.current_position}: {self} is out of range."
                )
            elif pitch_value < (start := instrument_range.start):
                pitch_value += 12 * math.ceil((start - pitch_value) / 12)
            elif pitch_value >= (stop := instrument_range.stop):
                pitch_value -= 12 * math.ceil((pitch_value - stop + 1) / 12)
            else:
                raise UNREACHABLE

        if self.instrument is None:
            # choose instrument based on pitch
            for _instrument, _range in INSTRUMENTS.items():
                if pitch_value in _range:
                    self.instrument = _instrument
                    self.note = _range.index(pitch_value)
                    break
            else:
                raise UNREACHABLE("Pitch_value was already checked to be in range")
        else:
            # choose note based on pitch and instrument
            self.note = instrument_range.index(pitch_value)

        if transpose:
            for name, value in ORIGINAL_PITCHES.items():
                if value == pitch_value:
                    self.name = name
                    break
            else:
                raise UNREACHABLE(pitch_value)

    def __str__(self):
        return self.name


class Rest(Note):
    def __init__(self, _voice: Voice):
        self.delay = _voice.tempo
        self.instrument = _voice.instrument
        self.note = 0
        self.dynamic = 0

    def __str__(self):
        return ""


class Bar(list[Note]):
    def __str__(self):
        return str([str(note) for note in self])

    def __repr__(self) -> str:
        return str([repr(note) for note in self])
