from __future__ import annotations

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
}


class Composition:
    def __init__(
        self,
        time: int,
        tempo: int,
        voices: list[dict],
        name: str = None,
        dynamic=2,
        transpose=0,
    ):
        self.time = time
        self.tempo = tempo
        self.name = name
        self.dynamic = dynamic
        self.transpose = transpose
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
        tempo: int = None,
        instrument: str = None,
        dynamic: int = None,
        transpose: int = None,
    ):
        self.time = _composition.time
        self.name = name
        self.instrument = instrument
        if tempo is None:
            tempo = _composition.tempo
        self.tempo = tempo
        if dynamic is None:
            dynamic = _composition.dynamic
        self.dynamic = dynamic
        if transpose is None:
            transpose = _composition.transpose
        self.transpose = transpose

        self._bars: list[Bar] = [Bar()]
        self._current_bar_length = 0
        for note in notes:
            if isinstance(note, str):
                note = {"name": note}
            self._add_note(**note)

    def __iter__(self):
        yield from self._bars

    def __str__(self):
        if self.name is not None:
            return self.name
        return super().__str__()

    def _config(
        self,
        tempo: int = None,
        instrument: str = None,
        dynamic: int = None,
        transpose: int = None,
    ):
        if instrument is not None:
            self.instrument = instrument
        if tempo is not None:
            self.tempo = tempo
        if dynamic is not None:
            self.dynamic = dynamic
        if transpose is not None:
            self.transpose = transpose

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
                if self._current_bar_length == self.time:
                    self._bars.append(Bar([note]))
                    self._current_bar_length = 1
                else:
                    self._bars[-1].append(note)
                    self._current_bar_length += 1
        else:
            self._config(**kwargs)


class Note:
    def __init__(
        self,
        _voice: Voice,
        pitch: str,
        instrument: str = None,
        dynamic: int = None,
        transpose: int = None,
    ):
        self.delay = _voice.tempo

        if transpose is None:
            transpose = _voice.transpose
        pitch_value = PITCHES[pitch] + transpose

        if instrument is None and (instrument := _voice.instrument) is None:
            # choose instrument based on pitch, error if none is in range
            for _instrument, _range in INSTRUMENTS.items():
                if pitch_value in _range:
                    self.instrument = instrument
                    self.note = _range.index(pitch_value)
                    break
            else:
                raise ValueError(f"{pitch_value} is out of range.")
        else:
            # choose note based on pitch and instrument, error if not in range
            self.instrument = instrument
            self.note = INSTRUMENTS[instrument].index(pitch_value)

        if dynamic is None:
            dynamic = _voice.dynamic
        self.dynamic = dynamic

        if transpose == 0:
            self._name = pitch
        else:
            for name, value in ORIGINAL_PITCHES.items():
                if value == pitch_value:
                    self._name = name

    def __str__(self):
        return self._name


class Rest(Note):
    def __init__(self, _voice: Voice):
        self.delay = _voice.tempo
        self.instrument = ""
        self.note = 0
        self.dynamic = 0

    def __str__(self):
        return ""


class Bar(list[Note]):
    def __str__(self):
        return str([str(note) for note in self])

    def __repr__(self) -> str:
        return str([repr(note) for note in self])
