from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional, Type, TypeVar

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


T = TypeVar("T")


def load_file(path: str | Path, *, expected_type: Type[T], strict: bool) -> T:
    def _find(path: Path, *, match_name: str = None) -> Optional[Path]:
        if not path.exists():
            return
        if path.is_dir():
            cwd, directories, files = next(os.walk(path))
            if len(files) == 1:
                return path / Path(files[0])
            for subpath in map(Path, files + directories):
                while (parent := path.parent) != path:
                    if find := _find(cwd / subpath, match_name=path.stem):
                        return find
                    path = parent
                path = Path(cwd)
        elif match_name is None or match_name == path.stem:
            return path

    if p := _find(path := Path(path)):
        with open(p, "r") as f:
            return json.load(f)

    error_message = f"Path {path} is invalid, or does not exist"
    if strict:
        raise UserError(error_message)

    logger.warn(error_message)
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w") as f:
        if expected_type is dict:
            f.write("{\n\n}")
        elif expected_type is list:
            f.write("[\n\n]")
    return expected_type()


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
            raise UserError(f"Delay must be in {DELAY_RANGE}")
        self.delay = delay

        if instrument is None:
            instrument = _voice.instrument
        self.instrument = instrument

        if dynamic is None:
            dynamic = _voice.dynamic
        if dynamic not in DYNAMIC_RANGE:
            raise UserError(f"Dynamic must be in {DYNAMIC_RANGE}")
        self.dynamic = dynamic

        try:
            pitch_value = PITCHES[pitch] + transpose
        except KeyError:
            raise UserError(f"{pitch} is not a valid note name")
        try:
            instrument_range = INSTRUMENTS[instrument]
        except KeyError:
            raise UserError(f"{instrument} is not a valid instrument")
        if pitch_value not in instrument_range:
            raise UserError(f"{self} is out of range for {instrument}")
        self.note = instrument_range.index(pitch_value)

    def __repr__(self):
        return self._name


class Rest(Note):
    def __init__(self, _voice: Voice, /, *, delay: int = None):
        if delay is None:
            delay = _voice.delay
        if delay not in DELAY_RANGE:
            raise UserError(f"Delay must be in {DELAY_RANGE}")
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
        notes: str | list[str | dict] = [],
        name: str = None,
        time: int = None,
        delay: int = None,
        beat: int = None,
        instrument: str = None,
        dynamic: int = None,
        transpose=0,
        sustain: bool | int | str = None,
        sustainDynamic: int | str = None,
    ):
        self._bar_number: int = 1
        self._beat_number: int = 1
        self._index = len(_composition)
        self._composition = _composition
        self._name = name

        notes = self._load_notes(notes)

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
        if sustain is None:
            sustain = _composition.sustain
        if sustainDynamic is None:
            sustainDynamic = _composition.sustainDynamic
        try:
            self._octave = (INSTRUMENTS[instrument].start - 6) // 12 + 2
        except KeyError:
            raise UserError(f"{self}: {instrument} is not a valid instrument")

        self.time = time
        self.division = _composition.division
        self.delay = delay
        self.beat = beat
        self.instrument = instrument
        self.dynamic = dynamic
        self.transpose = _composition.transpose + transpose
        self.sustain = sustain
        self.sustainDynamic = sustainDynamic

        self._note_config = {}
        self.append([])

        for note in notes:
            if len(self[-1]) == self.division:
                self.append([])
            kwargs = note if isinstance(note, dict) else {"name": note}
            if "name" in kwargs:
                try:
                    self._add_note(**(self._note_config | kwargs))
                except UserError as e:
                    raise UserError(
                        f"{self} at {(self._bar_number, self._beat_number)}: {e}"
                    )
            else:
                self._note_config |= kwargs

    def __str__(self):
        if self._name:
            return self._name
        return f"Voice {self._index + 1}"

    def _load_notes(
        self, notes_or_path_to_notes: str | list[str | dict]
    ) -> list[str | dict]:
        if isinstance(notes_or_path_to_notes, list):
            return notes_or_path_to_notes

        if self._name is None:
            self._name = notes_or_path_to_notes
        try:
            notes_or_another_voice = load_file(
                self._composition._path / Path(notes_or_path_to_notes),
                expected_type=list[str | dict],
                strict=False,
            )
        except Exception as e:
            raise UserError(f"{self}\n{type(e).__name__}: {e}")
        if isinstance(notes_or_another_voice, list):
            return notes_or_another_voice
        if "notes" not in notes_or_another_voice:
            return self._load_notes([])
        return self._load_notes(notes_or_another_voice["notes"])

    def _parse_note(self, value: str, beat: int):
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

    def _parse_duration(self, *values: str, beat: int) -> int:
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
            raise UserError(f"{value} is not a valid duration")

    def _Note(
        self,
        pitch: str,
        duration: int,
        *,
        beat: int,
        sustain: bool | int | str = None,
        sustainDynamic: int | str = None,
        trill: str = None,
        **kwargs,
    ) -> list[Note]:
        if pitch == "r":
            return self._Rest(duration, **kwargs)

        note = Note(self, pitch=pitch, **kwargs)

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
            sustain = duration
        if sustainDynamic is None:
            sustainDynamic = self.sustainDynamic

        if trill:
            trill_pitch, trill_duration = self._parse_note(trill, beat)
            if trill_duration < 0:
                trill_duration += duration
            if trill_duration < 0:
                trill_duration = 1
            if trill_duration > duration:
                trill_duration = duration
            alternating_notes = (note, Note(self, pitch=trill_pitch, **kwargs))
            out = [alternating_notes[i % 2] for i in range(trill_duration - 1)]
            out += self._Note(
                pitch=(pitch, trill_pitch)[(trill_duration - 1) % 2],
                duration=duration - trill_duration + 1,
                sustain=max(0, sustain - trill_duration) + 1,
                sustainDynamic=sustainDynamic,
                beat=beat,
                **kwargs,
            )
            return out

        instrument = kwargs["instrument"] if "instrument" in kwargs else self.instrument
        delay = kwargs["delay"] if "delay" in kwargs else self.delay
        if sustainDynamic is None:
            sustainDynamic = "+0" if instrument == "flute" and delay == 1 else "-2"
        if isinstance(sustainDynamic, str):
            sustainDynamic = max(
                min(1, note.dynamic), note.dynamic + int(sustainDynamic)
            )
        return (
            [note]
            + [Note(self, pitch=pitch, **kwargs | {"dynamic": sustainDynamic})]
            * (sustain - 1)
            + self._Rest(duration - sustain, **kwargs)
        )

    def _Rest(self, duration: int, *, delay: int = None, **kwargs) -> list[Note]:
        return [Rest(self, delay=delay)] * duration

    def _add_note(self, *, name: str, time: int = None, beat: int = None, **kwargs):
        if time is None:
            time = self.time
        if beat is None:
            beat = self.beat

        # allow multiple notes in one string, separated by commas
        # greatly reduce number of keystrokes when writing
        if len(names := name.split(",")) > 1:
            for name in names:
                self._add_note(name=name, time=time, beat=beat, **kwargs)
            return

        # Bar helpers
        # "|" to assert the beginning of a bar
        if name.startswith("|"):
            name = name[1:]
            # "||" to assert the beginning of a bar AND rest the entire bar
            rest = False
            if name.startswith("|"):
                name = name[1:]
                rest = True
            # if end with a bang, force assertion
            force = False
            if name.endswith("!"):
                name = name[:-1]
                force = True
            # bar number
            try:
                asserted_bar_number = int(name)
            except ValueError:
                raise UserError(f"Bar number must be an int, found {name}")
            # force or assert
            if force:
                self._beat_number = 1
                self._bar_number = asserted_bar_number
            elif self._beat_number != 1:
                raise UserError("Wrong barline location")
            elif self._bar_number != asserted_bar_number:
                raise UserError(
                    f"Expected bar {self._bar_number}, found {asserted_bar_number}"
                )
            # rest
            if rest:
                self._add_note(name=f"r {time}", time=time, **kwargs)
            return

        # actual note
        pitch, duration = self._parse_note(name, beat)
        if duration < 1:
            raise UserError("Note duration must be at least 1")
        # organize into divisions
        for note in self._Note(pitch, duration, beat=beat, **kwargs):
            if len(self[-1]) < self.division:
                self[-1].append(note)
            else:
                self.append([note])
        # update bar and beat number
        div, mod = divmod(self._beat_number + duration, time)
        self._beat_number = mod
        self._bar_number += div


class Composition(list[list[Voice]]):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(
        self,
        *,
        _path: Path,
        voices: list[dict | str] | list[list[dict | str]] = [[{}]],
        time=16,
        division: int = None,
        delay=1,
        beat=1,
        instrument="harp",
        dynamic=2,
        transpose=0,
        sustain=False,
        sustainDynamic: int | str = None,
    ):
        self._path = _path
        # values out of range are handled by Voice/Note.__init__
        self.time = time
        self.delay = delay
        self.beat = beat
        self.instrument = instrument
        self.dynamic = dynamic
        self.transpose = transpose
        self.sustain = sustain
        self.sustainDynamic = sustainDynamic

        if division is None:
            for n in range(16, 11, -1):
                if time % n == 0 or n % time == 0:
                    division = n
                    break
            else:
                division = time
        elif division <= 0:
            raise UserError("Division must be posititve")
        if division not in range(12, 17):
            logger.warn(
                f"Division {division} is not ideal, a value from 12 to 16 is recommended"
            )
        self.division = division

        if isinstance(voices[0], list):
            for orchestra in voices:
                self._add_orchestra(orchestra)
        else:
            self._add_orchestra(voices)

        self._equalize_orchestras_size()
        self._equalize_voices_length()

    @property
    def size(self):
        return len(self[0])

    @property
    def length(self):
        return len(self[0][0])

    def _add_orchestra(self, voices):
        if not isinstance(voices, list):
            raise UserError(f"Expected a list of voices, found {type(voices).__name__}")
        if len(self) >= 2:
            raise UserError(f"Expected at most 2 orchestras, found {len(self)}")
        self.append([])
        for voice in voices:
            self._add_voice(voice)

    def _add_voice(self, voice_or_path_to_voice):
        if not (
            isinstance(voice_or_path_to_voice, str)
            or isinstance(voice_or_path_to_voice, dict)
        ):
            raise UserError(
                f"Expected a voice, found {type(voice_or_path_to_voice).__name__}"
            )

        try:
            if isinstance(voice_or_path_to_voice, str):
                path_to_voice = self._path / Path(voice_or_path_to_voice)
                voice = load_file(path_to_voice, expected_type=dict, strict=False)
                if "name" not in voice:
                    voice["name"] = voice_or_path_to_voice
            else:
                voice = voice_or_path_to_voice
            self[-1].append(Voice(self, **voice))
        except Exception as e:
            if isinstance(e, UserError):
                raise
            raise UserError(f"{voice_or_path_to_voice}\n" f"{type(e).__name__}: {e}")

    def _equalize_orchestras_size(self):
        size = max(map(len, self))
        for orchestra in self:
            for _ in range(size - len(orchestra)):
                orchestra.insert(0, Voice(self))

    def _equalize_voices_length(self):
        length = max(map(len, [v for orchestra in self for v in orchestra]))
        for orchestra in self:
            for voice in orchestra:
                rest = Rest(voice)
                for _ in range(self.division - len(voice[-1])):
                    voice[-1].append(rest)
                for _ in range(length - len(voice)):
                    voice.append([rest] * self.division)

    @classmethod
    def compile(cls, path_to_composition: str):
        logger.info("Compiling")
        try:
            composition = load_file(
                path_to_composition, expected_type=dict, strict=True
            )
        except Exception as e:
            if (error_type := type(e)) is UserError:
                raise
            raise UserError(f"{path_to_composition}\n" f"{error_type.__name__}: {e}")
        return cls(**composition, _path=Path(path_to_composition))
