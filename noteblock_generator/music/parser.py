from __future__ import annotations

import json
import operator
import os
import re
from copy import copy as shallowcopy
from dataclasses import dataclass
from itertools import chain, repeat, zip_longest
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Protocol

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
    T_Level,
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
        elif match_name is None or match_name == path.stem:
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
    def new(cls, index: int, src: T_Section, env: _BaseSection | _GlobalDefault):
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


class _BaseSingleSection(_BaseSection):
    def _process_voices(self, voices: Iterable[SingleDivisionVoice | DoubleDivisionVoice]):
        # voices are NOT necesarily of equal length, pad them with empty notes
        merged_voice = [list(e) for e in map(chain.from_iterable, zip_longest(*voices, fillvalue=[]))]
        if not all(unit.delay == step[0].delay for step in merged_voice for unit in step[1:]):
            raise ValueError("inconsistent delay")  # TODO: report where exactly
        return merged_voice


class SingleDivisionSection(_BaseSingleSection, list[list["SingleDivisionNote"]]):
    def __init__(self, index: int, src: T_SingleDivisionSection, env: _BaseSection | _GlobalDefault):
        super().__init__(index, src, env)
        voices = mutivalue_flatten(
            positional_map(SingleDivisionVoice, i, voice, self)
            for i, voice in enumerate(src.voices)
            if voice is not None
        )
        self += self._process_voices(voices)


class DoubleDivisionSection(_BaseSingleSection, list[list["DoubleDivisionNote"]]):
    def __init__(self, index: int, src: T_DoubleDivisionSection, env: _BaseSection | _GlobalDefault):
        super().__init__(index, src, env)
        voices = mutivalue_flatten(
            positional_map(DoubleDivisionVoice, i, voice, self)
            for i, voice in enumerate(src.voices)
            if voice is not None
        )
        self += self._process_voices(voices)


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
        self._notes = self._resolve_sequential_notes(src.notes)

    def __iter__(self):
        yield from self._notes

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

    def _resolve_parallel_notes(self, src: T_ParallelNotes) -> Iterable[Iterable[Note]]:
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
            return self._check_bar_assertion(note)
        if is_typeform(note, T_MultipleNotes):
            return self._resolve_multiple_notes(note)
        if is_typeform(note, T_CompoundNote):
            return self._resolve_compound_note(note)
        return self._resolve_regular_note(note)

    def _check_bar_assertion(self, src: T_BarDelimiter) -> Iterable[Iterable[Note]]:
        return ()  # TODO

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

    def _resolve_multiple_notes(self, _note: T_MultipleNotes) -> Iterable[Iterable[Note]]:
        individual_notes = strip_split(_note, ",")
        return chain.from_iterable(map(self._resolve_regular_note, individual_notes))

    def _resolve_compound_note(self, _note: T_CompoundNote) -> Iterable[Iterable[Note]]:
        note_stripped_parentheses = _note[1:-1]
        individual_notes = strip_split(note_stripped_parentheses, ",")
        return self._apply_phrasing(*chain.from_iterable(map(self._create_noteblocks, individual_notes)))

    def _resolve_trilled_note(
        self, note: T_NoteName, trill: T_NoteName, trill_style: T_TrillStyle
    ) -> Iterable[Iterable[Note]]:
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
        _delay = self.delay.resolve()
        _position = self.position.resolve()
        _beat = self.beat.resolve()
        _sustain = self.sustain.resolve(beat=_beat, note_duration=len(noteblocks))
        _dynamic = self.dynamic.resolve(beat=_beat, sustain_duration=_sustain, note_duration=len(noteblocks))

        def transform(*notes: NoteBlock | None, dynamic: list[T_StaticAbsoluteDynamic], position: T_Index):
            def apply_delay_and_position(noteblocks: Iterable[NoteBlock | None]) -> Iterable[Note]:
                return (
                    Note(noteblock=nb, delay=_delay, position=position, voice_name=self.name, where=(1, 1))  # TODO
                    for nb in noteblocks
                )

            def apply_dynamic(notes: Iterable[Note]) -> Iterable[Iterable[Note]]:
                return map(operator.mul, notes, dynamic)

            result = apply_dynamic(apply_delay_and_position(notes))
            if TYPE_CHECKING:
                # result is Iterable, this tells pyright it's specifically not T_Multivalue,
                result = list(result)
            return result

        parallel_lines = positional_map(transform, *noteblocks, dynamic=_dynamic, position=_position)
        if type(parallel_lines) is T_MultiValue:
            merged_line = map(chain.from_iterable, transpose(parallel_lines))
            return merged_line
        return parallel_lines


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


@dataclass(kw_only=True, slots=True)
class Note:
    # run-time-significant attributes
    noteblock: NoteBlock | None
    delay: T_Delay
    position: T_Index
    # for compile-time checks only
    voice_name: str
    where: tuple[int, int]

    def __mul__(self, dynamic: T_StaticAbsoluteDynamic):
        if self.noteblock is None:
            return (self,)
        if dynamic > 0:
            return repeat(self, dynamic)
        # no need to copy, we only __mul__ a freshly-created note
        self.noteblock = None
        return (self,)


class SingleDivisionNote(Protocol):
    noteblock: NoteBlock | None
    delay: T_Delay
    position: T_Level


class DoubleDivisionNote(Protocol):
    note: NoteBlock | None
    delay: T_Delay
    position: T_DoubleIndex
