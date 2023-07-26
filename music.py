from __future__ import annotations

import math

# MAPPING OF PITCH NAMES TO NUMERICAL VALUES
# create first octave
_first = ["c1", "cs1", "d1", "ds1", "e1", "f1", "fs1", "g1", "gs1", "a1", "as1", "b1"]
_octaves = [_first]
# dynamically extend to octave 7
for _ in range(6):
    _octaves.append([p[:-1] + str(int(p[-1]) + 1) for p in _octaves[-1]])
# flatten and convert to dict
_ORIGINAL_PITCHES = {
    name: value
    for value, name in enumerate([pitch for octave in _octaves for pitch in octave])
}
# extend accidentals
PITCHES = dict(_ORIGINAL_PITCHES)
for name, value in _ORIGINAL_PITCHES.items():
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
    None: range(79),
}


class _RequireTranspose(Exception):
    def __init__(self, value: int):
        self.value = value


def _parse_transpose(value: int | str):
    if isinstance(value, int):
        return value
    if value.lower()[-2:] == "oc":
        return 12 * int(value[:-2])
    return int(value)


class Note:
    def __init__(
        self,
        _voice: Voice,
        name: str,
        tempo: int = None,
        instrument: str = None,
        dynamic: int = None,
        transpose: str | int = 0,
        autoReplaceOctaveEquivalent: bool = None,
    ):
        try:
            int(name[-1])
        except ValueError:
            if (octave := _voice.octave) is None:
                raise ValueError(
                    f"{_voice} at {_voice.current_position}: Octave is missing."
                )
            name += str(octave)
        if tempo is None:
            tempo = _voice.tempo
        if instrument is None:
            instrument = _voice.instrument
        if dynamic is None:
            dynamic = _voice.dynamic
        if autoReplaceOctaveEquivalent is None:
            autoReplaceOctaveEquivalent = _voice.autoReplaceOctaveEquivalent

        self.name = name
        transpose = _voice.transpose + _parse_transpose(transpose)
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
            start, stop = instrument_range.start, instrument_range.stop
            if pitch_value < start:
                required_transpose = start - pitch_value
            else:
                required_transpose = stop - 1 - pitch_value
            if _voice.autoTranspose:
                raise _RequireTranspose(required_transpose)
            if not autoReplaceOctaveEquivalent:
                raise ValueError(
                    f"{_voice} at {_voice.current_position}: {self} is out of range"
                    + (f" for {instrument}." if instrument is not None else ".")
                )
            if pitch_value < start:
                pitch_value += 12 * math.ceil(required_transpose / 12)
            else:
                pitch_value += 12 * math.floor(required_transpose / 12)

        if self.instrument is None:
            # choose instrument based on pitch
            for _instrument, _range in INSTRUMENTS.items():
                if _instrument is not None and pitch_value in _range:
                    self.instrument = _instrument
                    self.note = _range.index(pitch_value)
                    break
        else:
            # choose note based on pitch and instrument
            self.note = instrument_range.index(pitch_value)

        if transpose:
            for name, value in _ORIGINAL_PITCHES.items():
                if value == pitch_value:
                    self.name = name
                    break

        _voice._notes.append(self)

    def __str__(self):
        return self.name


class Rest(Note):
    def __init__(self, _voice: Voice, tempo: int = None, **kwargs):
        if tempo is None:
            tempo = _voice.tempo
        self.delay = tempo
        self.dynamic = 0
        self.name = "r"
        _voice._notes.append(self)


class Voice(list[list[Note]]):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(
        self,
        _composition: Composition,
        notes: list[str | dict],
        name: str = None,
        time: int = None,
        tempo: int = None,
        beats: int = None,
        octave: int = None,
        instrument: str = None,
        dynamic: int = None,
        transpose: str | int = 0,
        autoReplaceOctaveEquivalent: bool = None,
    ):
        self._composition = _composition
        self._index = len(_composition)
        self.autoTranspose = _composition.autoTranspose
        self.name = name
        if time is None:
            time = _composition.time
        if tempo is None:
            tempo = _composition.tempo
        if beats is None:
            beats = _composition.beats
        if octave is None:
            octave = _composition.octave
        if instrument is None:
            instrument = _composition.instrument
        if dynamic is None:
            dynamic = _composition.dynamic
        if autoReplaceOctaveEquivalent is None:
            autoReplaceOctaveEquivalent = _composition.autoReplaceOctaveEquivalent

        self.beats = beats
        self.octave = octave
        self.time = time
        self._config(
            time=time,
            tempo=tempo,
            instrument=instrument,
            dynamic=dynamic,
            transpose=transpose,
            autoReplaceOctaveEquivalent=autoReplaceOctaveEquivalent,
        )

        self._notes: list[Note] = []
        if notes:
            self.append([])
        for note in notes:
            if isinstance(note, str):
                note = {"name": note}
            self._add_note(**note)

    @property
    def current_position(self):
        """For error message"""
        return (len(self), len(self[-1]) + 1)

    def __str__(self):
        if self.name:
            return self.name
        return f"Voice {self._index + 1}"

    def _config(
        self,
        time: int = None,
        tempo: int = None,
        beats: int = None,
        octave: int = None,
        instrument: str = None,
        dynamic: int = None,
        transpose: str | int = None,
        autoReplaceOctaveEquivalent: bool = None,
    ):
        if time is not None:
            self.time = time
        if tempo is not None:
            self.tempo = tempo
        if beats is not None:
            self.beats = beats
        if octave is not None:
            self.octave = octave
        if instrument is not None:
            self.instrument = instrument
        if dynamic is not None:
            self.dynamic = dynamic
        if transpose is not None:
            self.transpose = self._composition.transpose + _parse_transpose(transpose)
        if autoReplaceOctaveEquivalent is not None:
            self.autoReplaceOctaveEquivalent = autoReplaceOctaveEquivalent

    def _rest(self, duration: int, **kwargs) -> list[Note]:
        return [Rest(self, **kwargs) for _ in range(duration)]

    def _append(self, note: Note):
        self._add_note(name=f"{note.name} {1}", tempo=note.delay, dynamic=note.dynamic)

    def _parse_duration(self, value: str):
        if not value:
            if self.beats is not None:
                return self.beats
            else:
                raise ValueError("Duration is missing.")
        if value[-1] == ".":
            return int(self._parse_duration(value[:-1]) * 1.5)
        if value[-1] == "b":
            if self.beats is None:
                raise ValueError("Duration is missing.")
            return self.beats * int(value[:-1])
        elif value[-3:] == "bar":
            return self.time * int(value[:-3])
        else:
            return int(value)

    def _add_note(self, **kwargs):
        # prepare current bar
        if (L := len(self[-1])) == self.time:
            self.append([])
        elif L > self.time:
            raise ValueError(f"{self} at {self.current_position}: time error.")

        if "name" in kwargs:
            # parse note name
            _value = kwargs.pop("name").lower().split(maxsplit=1)

            # if note name is "||", fill the rest of the bar with rests
            if (pitch := _value[0]).startswith("||"):
                self[-1] += self._rest(self.time - len(self[-1]))
                return
            # if "|", do a bar check (self-enforced linter)
            if pitch.startswith("|"):
                if self[-1]:
                    raise ValueError(f"{self} at {self.current_position}: time error.")
                return
            # we do ".startswith" rather than "=="
            # so that "|" or "||" can be followed by a numberc,
            # acting as the bar number, even though this number is not checked

            # read duration
            try:
                duration = _value[1]
            except IndexError:
                duration = ""
            delay = self._parse_duration(duration)

            # divide note into actual note + rests
            if pitch == "r":
                notes = self._rest(delay, **kwargs)
            else:
                notes = [Note(self, pitch, **kwargs)] + self._rest(delay - 1, **kwargs)

            # organize those into barss
            for note in notes:
                if len(self[-1]) < self.time:
                    self[-1].append(note)
                else:
                    self.append([note])

        elif "copy" in kwargs:
            _value = kwargs.pop("copy").lower().split(maxsplit=1)
            other_voice = self._composition[_value[0]]
            L = len(self._notes)

            self._config(**kwargs)

            if len(_value) == 2:
                duration = self._parse_duration(_value[1])
                try:
                    for note in other_voice._notes[L : L + duration]:
                        self._append(note)
                except IndexError:
                    raise ValueError(f"{self} at {self.current_position}: time error.")
            else:
                for note in other_voice._notes[L:]:
                    self._append(note)

        else:
            self._config(**kwargs)


class Composition(list[Voice]):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(
        self,
        time: int,
        tempo: int,
        voices: list[dict],
        beats: int = None,
        octave: int = None,
        instrument: str = None,
        dynamic=2,
        transpose: str | int = 0,
        autoTranspose=False,
        autoReplaceOctaveEquivalent=False,
    ):
        self.time = time
        self.tempo = tempo
        self.beats = beats
        self.octave = octave
        self.instrument = instrument
        self.dynamic = dynamic
        self.transpose = _parse_transpose(transpose)
        self.autoTranspose = autoTranspose
        self.autoReplaceOctaveEquivalent = autoReplaceOctaveEquivalent

        self._auto_transpose = 0
        while True:
            if not self.autoTranspose:
                return self._set_voices(voices)
            try:
                return self._set_voices(voices)
            except _RequireTranspose as e:
                value = e.value
                if self._auto_transpose * value < 0:
                    # no transpose available, revert all attempts to autoTranspose
                    self.autoTranspose = False
                    self.transpose = _parse_transpose(transpose)
                    self._auto_transpose = 0
                else:
                    self._auto_transpose += value
                    self.transpose += value
                self.clear()

    def _set_voices(self, voices: list[dict]):
        for voice in voices:
            self.append(Voice(self, **voice))
        if (transpose := self._auto_transpose) > 0:
            print(f"autoTransposed: +{transpose}")
        elif transpose < 0:
            print(f"autoTransposed: {transpose}")

    def __getitem__(self, key: int | str) -> Voice:
        if isinstance(key, int):
            return self[key]
        for voice in self:
            if voice.name == key:
                return voice
        raise KeyError(key)
