from __future__ import annotations

import json
import operator
import os
import re
from copy import copy as shallowcopy
from dataclasses import dataclass
from itertools import chain, repeat, zip_longest
from pathlib import Path
from typing import Iterable, Protocol

from pydantic import TypeAdapter

from .properties import (
    Beat,
    Delay,
    DoubleDivisionPosition,
    Dynamic,
    GlobalPosition,
    Instrument,
    Name,
    NoteBlock,
    SingleDivisionPosition,
    Sustain,
    Tick,
    Time,
    Transpose,
    TrillStyle,
    Width,
)
from .typedefs import (
    T_BarDelimiter,
    T_CompoundNote,
    T_CompoundSection,
    T_Delay,
    T_DoubleDivisionSection,
    T_DoubleDivisionVoice,
    T_DoubleIndex,
    T_Duration,
    T_Index,
    T_LevelIndex,
    T_MultipleNotes,
    T_MultiValue,
    T_NoteMeta,
    T_NoteName,
    T_NotesModifier,
    T_ParallelNotes,
    T_Positional,
    T_Rest,
    T_Section,
    T_SequentialNotes,
    T_SingleDivisionSection,
    T_SingleDivisionVoice,
    T_SingleNote,
    T_StaticAbsoluteDynamic,
    T_TrilledNote,
    T_TrillStyle,
    T_Voice,
)
from .utils import (
    is_typeform,
    mutivalue_flatten,
    parse_duration,
    parse_timedvalue,
    positional_map,
    strip_split,
    transpose,
)


def parse(path_in: str) -> list[Section]:
    def flatten(section: CompoundSection | Section) -> list[Section]:
        if isinstance(section, Section):
            return [section]
        out = []
        for subsection in section:
            out += flatten(subsection)
        return out

    data = _resolve_references(f'"file://{path_in}"', prefix=Path.cwd())
    validated_data = TypeAdapter(T_Section).validate_json(data)  # TODO: error handling
    return flatten(_BaseSection.new(0, validated_data, _GlobalDefault()))


_URI_PATTERN = re.compile(r'"file://([^"]+)"')


def _resolve_references(source: str, *, prefix: Path) -> str:
    offset = 0
    for m in _URI_PATTERN.finditer(source):
        match, match_path = m.group(0, 1)
        path = _find_path(prefix / match_path)
        replacement = _load_reference(path)
        start = m.start() + offset
        end = m.end() + offset
        source = source[:start] + replacement + source[end:]
        offset += len(replacement) - len(match)
    return source


def _find_path(path: Path):
    def find(path: Path, /, *, match_name: str = None) -> Path | None:
        if path.is_dir():
            cwd, directories, files = next(os.walk(path))
            files = [f for f in files if f.endswith(".json")]
            if len(files) == 1:
                return path / Path(files[0])
            for subpath in map(Path, files + directories):
                while (parent := path.parent) != path:
                    if found := find(cwd / subpath, match_name=path.stem):
                        return found
                    path = parent
                path = Path(cwd)
            return None
        if match_name is None or match_name == path.stem:
            return path

    if not path.exists():
        raise ValueError(f"{path} does not exist")
    if not (found := find(path)):
        raise ValueError(f"unrecognized music format for {path}")
    return found


def _load_reference(path: Path):
    text = _resolve_references(path.read_text(), prefix=path.parent)
    if isinstance(obj := json.loads(text), dict):
        obj["path"] = str(path)
    else:
        obj = {"path": str(path), "data": obj}
    return json.dumps(obj)


class _GlobalDefault:
    name = Name()
    time = Time()
    width = Width()
    delay = Delay()
    beat = Beat()
    tick = Tick()
    trill_style = TrillStyle()
    position = GlobalPosition()
    instrument = Instrument()
    dynamic = Dynamic()
    sustain = Sustain()
    transpose = Transpose()


class _BaseSection:
    @classmethod
    def new(cls, index: int, src: T_Section, env: _BaseSection | _GlobalDefault) -> Section | CompoundSection:
        if isinstance(src, T_SingleDivisionSection):
            return SingleDivisionSection(index, src, env)
        if isinstance(src, T_DoubleDivisionSection):
            return DoubleDivisionSection(index, src, env)
        return CompoundSection(index, src, env)

    def __init__(self, index: int, src: T_Section, env: _BaseSection | _GlobalDefault):
        self.name = env.name.transform(index, src)
        self.time = env.time.transform(src.time)
        self.width = env.width.transform(self.time.resolve(), src.width)
        self.delay = env.delay.transform(src.delay)
        self.beat = env.beat.transform(src.beat)
        self.tick = env.tick.transform(src.tick)
        self.trill_style = env.trill_style.transform(src.trill_style)
        self.position = env.position.transform(src.position)
        self.instrument = env.instrument.transform(src.instrument)
        self.dynamic = env.dynamic.transform(src.dynamic)
        self.sustain = env.sustain.transform(src.sustain)
        self.transpose = env.transpose.transform(src.transpose)


class CompoundSection(_BaseSection, list["Section | CompoundSection"]):
    def __init__(self, index: int, src: T_CompoundSection, env: _BaseSection | _GlobalDefault):
        super().__init__(index, src, env)
        for index, subsection in enumerate(src.sections):
            self.append(self.new(index, subsection, self))


def _process_voices(voices: Iterable[Voice]):
    sequential_notes: list[list[Note]] = []
    # voices are not necesarily of equal length, pad them with empty notes
    merged_line = map(chain.from_iterable, zip_longest(*voices, fillvalue=[]))
    for step_iter in merged_line:
        # step_iter is guaranteed to have at least one element (see _Note.__mul__)
        parallel_notes = [first := next(step_iter)]
        for note in step_iter:
            if first.delay != note.delay:
                raise ValueError(f"inconsistent delays: {first}(delay={first.delay}) and {note}(delay={note.delay})")
            if first.where != note.where:
                raise ValueError(f"inconsistent placements: {first} and {note}")
            parallel_notes.append(note)
        sequential_notes.append(parallel_notes)
    return sequential_notes


class SingleDivisionSection(_BaseSection, list[list["SingleDivisionNote"]]):
    def __init__(self, index: int, src: T_SingleDivisionSection, env: _BaseSection | _GlobalDefault):
        super().__init__(index, src, env)
        voices = mutivalue_flatten(
            positional_map(SingleDivisionVoice, i, voice, self)
            for i, voice in enumerate(src.voices)
            if voice is not None
        )
        self += _process_voices(voices)


class DoubleDivisionSection(_BaseSection, list[list["DoubleDivisionNote"]]):
    def __init__(self, index: int, src: T_DoubleDivisionSection, env: _BaseSection | _GlobalDefault):
        super().__init__(index, src, env)
        voices = mutivalue_flatten(
            positional_map(DoubleDivisionVoice, i, voice, self)
            for i, voice in enumerate(src.voices)
            if voice is not None
        )
        self += _process_voices(voices)


Section = SingleDivisionSection | DoubleDivisionSection


class _BaseVoice:
    position: SingleDivisionPosition | DoubleDivisionPosition

    def __init__(self, index: T_LevelIndex, src: T_Voice, env: Section):
        self.name = env.name.transform(index, src).resolve()
        self.time = env.time.transform(src.time, save=True)
        self.delay = env.delay.transform(None, save=True)
        self.beat = env.beat.transform(src.beat, save=True)
        self.trill_style = env.trill_style.transform(src.trill_style, save=True)
        self.position = self.position.apply_globals(env.position).transform(src.position, save=True)
        self.instrument = env.instrument.transform(src.instrument, save=True)
        self.dynamic = env.dynamic.transform(src.dynamic, save=True)
        self.sustain = env.sustain.transform(src.sustain, save=True)
        self.transpose = env.transpose.transform(src.transpose, save=True)
        self.current_bar = 1  # bar indexing starts from 1
        self.current_beat = 0  # but beat starts from 0
        self._notes = _NotesFactory(self).resolve(src.notes)

    def __iter__(self):
        yield from self._notes


class SingleDivisionVoice(_BaseVoice, Iterable[Iterable["SingleDivisionNote"]]):
    def __init__(self, index: T_LevelIndex, src: T_SingleDivisionVoice, env: SingleDivisionSection):
        # I don't know if this is a pydantic BUG?
        # but sometimes `src` is not converted into a T_Voice but remains a dict,
        # so we force pydantic to convert the type again.
        # Performance impact is negligible (if measureable at all), don't even think about it.
        src = T_SingleDivisionVoice.model_validate(src)
        self.position = SingleDivisionPosition(index)
        super().__init__(index, src, env)


class DoubleDivisionVoice(_BaseVoice, Iterable[Iterable["DoubleDivisionNote"]]):
    def __init__(self, index: T_LevelIndex, src: T_DoubleDivisionVoice, env: DoubleDivisionSection):
        # See comment in SingleDivisionVoice.__init__
        src = T_DoubleDivisionVoice.model_validate(src)
        self.position = DoubleDivisionPosition(index)
        super().__init__(index, src, env)


Voice = SingleDivisionVoice | DoubleDivisionVoice


class _NotesFactory:
    def __init__(self, env: _BaseVoice):
        self.name = env.name
        self.time = env.time
        self.delay = env.delay
        self.beat = env.beat
        self.trill_style = env.trill_style
        self.position = env.position
        self.instrument = env.instrument
        self.dynamic = env.dynamic
        self.sustain = env.sustain
        self.transpose = env.transpose
        self._env = env

    @property
    def current_bar(self):
        return self._env.current_bar

    @current_bar.setter
    def current_bar(self, value: int):
        self._env.current_bar = value

    @property
    def current_beat(self):
        return self._env.current_beat

    @current_beat.setter
    def current_beat(self, value: int):
        self._env.current_beat = value

    def resolve(self, src: T_SequentialNotes):
        return self._resolve_sequential_notes(src)

    def _transform(self, src: T_NoteMeta):
        self.time = self.time.transform(src.time)
        self.delay = self.delay.transform(src.delay)
        self.beat = self.beat.transform(src.beat)
        self.trill_style = self.trill_style.transform(src.trill_style)
        self.position = self.position.transform(src.position)
        self.instrument = self.instrument.transform(src.instrument)
        self.dynamic = self.dynamic.transform(src.dynamic)
        self.sustain = self.sustain.transform(src.sustain)
        self.transpose = self.transpose.transform(src.transpose)

    def _resolve_sequential_notes(self, src: T_SequentialNotes):
        self = shallowcopy(self)
        self._transform(src)

        def _resolve_core(note: T_SingleNote | T_ParallelNotes | T_NotesModifier) -> Iterable[Iterable[Note]]:
            if isinstance(note, T_SingleNote):
                return self._resolve_single_note(note)
            if isinstance(note, T_ParallelNotes):
                return self._resolve_parallel_notes(note)
            self._transform(note)
            return ()

        sequential_lines = map(_resolve_core, src.note)
        merged_line = chain.from_iterable(sequential_lines)
        return merged_line

    def _resolve_parallel_notes(self, src: T_ParallelNotes):
        self = shallowcopy(self)
        self._transform(src)

        def _resolve_core(note: T_SingleNote | T_SequentialNotes) -> Iterable[Iterable[Note]]:
            if isinstance(note, T_SingleNote):
                return self._resolve_single_note(note)
            return self._resolve_sequential_notes(note)

        parallel_lines = map(_resolve_core, src.note)
        # fail if parallel lines written by the user are not of the same length # TODO: error handling
        merged_line = map(chain.from_iterable, transpose(parallel_lines))
        return merged_line

    def _resolve_single_note(self, src: T_SingleNote) -> Iterable[Iterable[Note]]:
        self = shallowcopy(self)
        self._transform(src)

        if isinstance(src, T_TrilledNote):
            trill_style = self.trill_style.resolve()
            return self._resolve_trilled_note(src.note, src.trill, trill_style)
        if is_typeform(note := src.note, T_BarDelimiter):
            return self._resolve_bar_delimiter(note)
        if is_typeform(note, T_MultipleNotes):
            return self._resolve_multiple_notes(note)
        if is_typeform(note, T_CompoundNote):
            return self._resolve_compound_note(note)
        return self._resolve_regular_note(note)

    def _resolve_bar_delimiter(self, src: T_BarDelimiter) -> Iterable[Iterable[Note]]:
        # TODO: error handling

        if src.startswith("||"):
            rest = True
            src = src[2:].lstrip()
        else:
            rest = False
            src = src[1:].lstrip()

        if src.endswith("!"):
            force_assertion = True
            asserted_bar_number = src[:-1]
        else:
            force_assertion = False
            asserted_bar_number = src

        if not is_typeform(asserted_bar_number, int, strict=False):
            raise ValueError(f"bar number must be an int, found {asserted_bar_number}")
        asserted_bar_number = int(asserted_bar_number)

        if force_assertion:
            self.current_beat = 0
            self.current_bar = asserted_bar_number
        elif self.current_beat != 0:
            raise ValueError("wrong barline location")
        elif self.current_bar != asserted_bar_number:
            raise ValueError("wrong bar number")

        if rest:
            return self._resolve_regular_note(f"r {self.time.resolve()}")
        return ()

    def _parse_note(self, src: T_NoteName | T_Rest) -> tuple[T_Positional[NoteBlock] | None, T_Duration]:
        tokens = parse_timedvalue(src)
        note_name = tokens[0].lower()
        note_duration = parse_duration(*tokens[1:], beat=self.beat.resolve())

        if note_name == "r":
            return None, note_duration
        note = self.instrument.resolve(note_name, transpose=self.transpose.resolve())  # TODO: error handling
        return note, note_duration

    def _create_noteblocks(self, src: T_NoteName | T_Rest) -> Iterable[T_Positional[NoteBlock] | None]:
        note, duration = self._parse_note(src)
        if duration <= 0:
            raise ValueError("Note duration must be positive")  # TODO error handling
        return repeat(note, duration)

    def _resolve_regular_note(self, _note: T_NoteName | T_Rest) -> Iterable[Iterable[Note]]:
        return self._apply_phrasing(*self._create_noteblocks(_note))

    def _resolve_multiple_notes(self, _note: T_MultipleNotes):
        individual_notes = strip_split(_note, ",")
        return chain.from_iterable(map(self._resolve_regular_note, individual_notes))

    def _resolve_compound_note(self, _note: T_CompoundNote):
        note_stripped_parentheses = _note[1:-1]
        individual_notes = strip_split(note_stripped_parentheses, ",")
        return self._apply_phrasing(*chain.from_iterable(map(self._create_noteblocks, individual_notes)))

    def _resolve_trilled_note(self, note: T_NoteName, trill: T_NoteName, trill_style: T_TrillStyle):
        noteblocks = list(self._create_noteblocks(note))
        note_duration = len(noteblocks)
        trill_noteblock, trill_duration = self._parse_note(trill)
        if trill_duration < 0:
            trill_duration += note_duration
        # if a trill only lasted one pulse, it wouldn't be a trill,
        # unless the main note also lasts only one pulse
        trill_duration = max(trill_duration, min(note_duration, 2))

        place_trill_here = (lambda i: i % 2 == 0) if trill_style == "alt" else (lambda i: i % 2 == 1)
        for i in range(trill_duration):
            if place_trill_here(i):
                noteblocks[i] = trill_noteblock
        return self._apply_phrasing(*noteblocks)

    def _apply_phrasing(self, *noteblocks: T_Positional[NoteBlock] | None) -> Iterable[Iterable[Note]]:
        note_duration = len(noteblocks)
        time = self.time.resolve()
        beat = self.beat.resolve()
        delay = self.delay.resolve()
        position = self.position.resolve()
        sustain = self.sustain.resolve(beat=beat, note_duration=note_duration)
        dynamic = self.dynamic.resolve(beat=beat, sustain_duration=sustain, note_duration=note_duration)

        def transform(*noteblocks: NoteBlock | None, dynamic: list[T_StaticAbsoluteDynamic], position: T_Index):
            def apply_delay_and_position(noteblocks: Iterable[NoteBlock | None]) -> Iterable[Note]:
                for noteblock in noteblocks:
                    yield self._create_note(noteblock=noteblock, delay=delay, position=position)
                    if (beat := self.current_beat + 1) < time:
                        self.current_beat = beat
                    else:
                        self.current_beat = 0
                        self.current_bar += 1

            def apply_dynamic(notes: Iterable[Note]) -> Iterable[Iterable[Note]]:
                return map(operator.mul, notes, dynamic)

            return apply_dynamic(apply_delay_and_position(noteblocks))

        parallel_lines = positional_map(transform, *noteblocks, dynamic=dynamic, position=position)
        if type(parallel_lines) is T_MultiValue:
            merged_line = map(chain.from_iterable, transpose(parallel_lines))
            return merged_line
        return parallel_lines

    def _create_note(self, *, noteblock: NoteBlock | None, delay: T_Delay, position: T_Index) -> Note:
        return _Note(
            noteblock=noteblock,
            delay=delay,
            position=position,
            voice=self.name,
            where=(self.current_bar, self.current_beat),
        )  # pyright: ignore[reportGeneralTypeIssues]


@dataclass(kw_only=True, slots=True)
class _Note:
    # run-time-significant attributes
    noteblock: NoteBlock | None
    delay: T_Delay
    position: T_Index
    voice: str  # for error messages
    where: tuple[int, int]  # for compile-time checks

    def __mul__(self, dynamic: T_StaticAbsoluteDynamic):
        if self.noteblock is None:
            dynamic = 1
        elif dynamic == 0:
            # no need to copy, we only __mul__ a freshly-created note
            self.noteblock = None
        return repeat(self, dynamic)

    def __repr__(self):
        return f"{self.voice}@{self.where}"


class SingleDivisionNote(Protocol):
    noteblock: NoteBlock | None
    delay: T_Delay
    position: T_LevelIndex
    voice: str
    where: tuple[int, int]


class DoubleDivisionNote(Protocol):
    noteblock: NoteBlock | None
    delay: T_Delay
    position: T_DoubleIndex
    voice: str
    where: tuple[int, int]


Note = SingleDivisionNote | DoubleDivisionNote
