from __future__ import annotations

# MAPPING OF PITCH NAMES TO NUMERICAL VALUES
# create first octave
_first = ["c1", "cs1", "d1", "ds1", "e1", "f1", "fs1", "g1", "gs1", "a1", "as1", "b1"]
_octaves = [_first]
# dynamically extend to octave 7
for _ in range(6):
    _octaves.append([p[:-1] + str(int(p[-1]) + 1) for p in _octaves[-1]])
# flatten and convert to dict
_PITCHES = {
    name: value
    for value, name in enumerate([pitch for octave in _octaves for pitch in octave])
}
# extend accidentals
for name, value in dict(_PITCHES).items():
    if name[-2] == "s":
        # double sharps
        if value + 1 < 84:
            _PITCHES[name[:-1] + "s" + name[-1]] = value + 1
            _PITCHES[name[:-2] + "x" + name[-1]] = value + 1
    else:
        # flats
        if value - 1 >= 0:
            _PITCHES[name[:-1] + "b" + name[-1]] = value - 1
        # double flats
        if value - 2 >= 0:
            _PITCHES[name[:-1] + "bb" + name[-1]] = value - 2

# MAPPING OF INSTRUMENTS TO NUMERICAL RANGES
_INSTRUMENTS = {
    "bass": range(6, 30),
    "didgeridoo": range(6, 30),
    "guitar": range(18, 42),
    "harp": range(30, 54),
    "bit": range(30, 54),
    "banjo": range(30, 54),
    "iron_xylophone": range(30, 54),
    "pling": range(30, 54),
    "flute": range(42, 66),
    "cow_bell": range(42, 66),
    "bell": range(54, 78),
    "xylophone": range(54, 78),
    "chime": range(54, 78),
    "basedrum": range(78),
    "hat": range(78),
    "snare": range(78),
}


class Composition:
    def __init__(
        self,
        time: int,
        tempo: int,
        name: str = None,
        dynamic=2,
        transpose=0,
    ):
        self._voices: list[Voice] = []
        self.time = time
        self.tempo = tempo
        self.name = name
        self.dynamic = dynamic
        self.transpose = transpose

    def __iter__(self):
        yield from self._voices

    def __str__(self):
        if self.name is not None:
            return self.name
        return super().__str__()

    def add_voice(self, **kwargs) -> Voice:
        self._voices.append(voice := Voice(self, **kwargs))
        return voice

    def generate(self, path: str):
        """TODO"""


class Voice:
    def __init__(
        self,
        _comp: Composition,
        name: str = None,
        tempo: int = None,
        instrument: str = None,
        dynamic: int = None,
        transpose: int = None,
    ):
        if dynamic is None:
            dynamic = _comp.dynamic
        if transpose is None:
            transpose = _comp.transpose
        if tempo is None:
            tempo = _comp.tempo

        self._bars: list[Bar] = [Bar()]  # list of notes divided into bars
        self._current_bar_length = 0

        self.time = _comp.time
        self.name = name
        self.instrument = instrument
        self._config(tempo, instrument, dynamic, transpose)

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
        self.instrument = instrument
        if tempo is not None:
            self.tempo = tempo
        if dynamic is not None:
            self.dynamic = dynamic
        if transpose is not None:
            self.transpose = transpose

    def _rest(self, duration: int) -> list[Note]:
        return [_Rest(self)] * duration

    def add_note(self, **kwargs):
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
        self.pitch = pitch
        self.delay = _voice.tempo

        if transpose is None:
            transpose = _voice.transpose
        pitch_value = _PITCHES[pitch] + transpose

        if instrument is None and (instrument := _voice.instrument) is None:
            # choose instrument based on pitch
            for _instrument, _range in _INSTRUMENTS.items():
                if pitch_value in _range:
                    self.instrument = instrument
                    self.note = _range.index(pitch_value)
        else:
            # choose note based on pitch and instrument, error if not in range
            self.instrument = instrument
            self.note = _INSTRUMENTS[instrument].index(pitch_value)

        if dynamic is None:
            dynamic = _voice.dynamic
        self.dynamic = dynamic

    def __str__(self):
        return self.pitch


class _Rest(Note):
    def __init__(self, _voice: Voice):
        self.delay = _voice.tempo
        self.instrument = ""
        self.note = 0
        self.dynamic = 0

    def __str__(self):
        return "r"


class Bar(list[Note]):
    def __str__(self):
        return str([str(note) for note in self])

    def __repr__(self) -> str:
        return str([repr(note) for note in self])
