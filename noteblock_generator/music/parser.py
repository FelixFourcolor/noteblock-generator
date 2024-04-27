from __future__ import annotations

import operator
from collections import deque
from contextlib import contextmanager
from copy import copy as shallowcopy
from dataclasses import dataclass
from itertools import chain, repeat, zip_longest
from typing import Iterable, Iterator, Protocol, cast

from pydantic import TypeAdapter

from .properties import (
    Beat,
    Continuous,
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
    T_Delay,
    T_DoubleDivisionSection,
    T_DoubleDivisionVoice,
    T_DoubleIndex,
    T_Duration,
    T_Index,
    T_LevelIndex,
    T_MultipleNotes,
    T_MultiSection,
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
    T_Tick,
    T_TrilledNote,
    T_TrillStyle,
    T_Tuple,
    T_Voice,
    T_Width,
)
from .utils import (
    is_typeform,
    multivalue_flatten,
    parse_duration,
    positional_map,
    split_timedvalue,
    strip_split,
    transpose,
)


def parse(src_code: str):
    return Music(src_code)  # TODO: error handling


class Unit(T_Tuple[NoteBlock]):
    delay: T_Delay

    def __new__(cls, notes: Iterable[Note], *, delay: T_Delay):
        def get_noteblocks(notes: Iterable[Note]) -> Iterable[NoteBlock]:
            for note in notes:
                if (noteblock := note.noteblock) is not None:
                    yield noteblock

        self = super().__new__(cls, get_noteblocks(notes := tuple(notes)))
        if len(self) > Dynamic.MAX:
            raise ValueError(f"Slot overflow: {notes}")  # TODO: error handling
        self.delay = delay
        return self  # TODO: optimization: not every unit needs to be rendered

    def __bool__(self):
        return bool(filter(None, self))


class SingleDivision(list[list[Unit]]):
    @classmethod
    def from_src(cls, sequential_notes: SingleDivisionSection, *, min_level: T_LevelIndex, max_level: T_LevelIndex):
        def assign_levels(parallel_notes: list[SingleDivisionNote]) -> Iterable[Unit]:
            delay = parallel_notes[0].delay
            return (
                Unit(filter(lambda note: note.position == level, parallel_notes), delay=delay)
                for level in range(min_level, max_level + 1)
            )

        return cls(
            transpose(map(assign_levels, sequential_notes)),
            width=sequential_notes.width.resolve(),
            tick=sequential_notes.tick.resolve(),
        )

    def __init__(self, sequence: Iterable[Iterable[Unit]], *, width: T_Width, tick: T_Tick):
        self.width = width
        self.tick = tick
        self += map(list, sequence)

    @property
    def length(self):
        return len(self[0])

    @property
    def height(self):
        return len(self)


class DoubleDivision(tuple[SingleDivision, SingleDivision]):
    @classmethod
    def from_src(cls, sequential_notes: DoubleDivisionSection, *, min_level: T_LevelIndex, max_level: T_LevelIndex):
        def assign_levels_left(parallel_notes: list[DoubleDivisionNote]) -> Iterable[Unit]:
            delay = parallel_notes[0].delay
            return (
                Unit(
                    filter(lambda note: note.position[0] == 0 and note.position[1] == level, parallel_notes),  # type: ignore # pyright bug # noqa: PGH003
                    delay=delay,
                )
                for level in range(min_level, max_level + 1)
            )

        def assign_levels_right(parallel_notes: list[DoubleDivisionNote]) -> Iterable[Unit]:
            delay = parallel_notes[0].delay
            return (
                Unit(
                    filter(lambda note: note.position[0] == 1 and note.position[1] == level, parallel_notes),  # type: ignore # pyright bug # noqa: PGH003
                    delay=delay,
                )
                for level in range(min_level, max_level + 1)
            )

        width = sequential_notes.width.resolve()
        tick = sequential_notes.tick.resolve()
        left_division = SingleDivision(transpose(map(assign_levels_left, sequential_notes)), width=width, tick=tick)
        right_division = SingleDivision(transpose(map(assign_levels_right, sequential_notes)), width=width, tick=tick)

        return cls((left_division, right_division))

    @property
    def width(self):
        return self[0].width

    @property
    def tick(self):
        return self[0].tick

    @property
    def length(self):
        return self[0].length

    @property
    def height(self):
        return self[0].height


T_Subsection = SingleDivision | DoubleDivision


class Section(list[T_Subsection]):
    def __init__(self, src: CompoundSection, *, min_level: T_LevelIndex, max_level: T_LevelIndex):
        # TODO: initial padding
        for subsection in src:
            if isinstance(subsection, SingleDivisionSection):
                self.append(SingleDivision.from_src(subsection, min_level=min_level, max_level=max_level))
            else:
                self.append(DoubleDivision.from_src(subsection, min_level=min_level, max_level=max_level))

        self.length = sum(subsection.length for subsection in self)
        self.height = self[0].height


class Music(list[Section]):
    def __init__(self, src_code: str):
        validated_data = TypeAdapter(T_Section).validate_json(src_code)
        parsed_data = MultiSection.subsection(_DefaultEnvironment(), 0, validated_data)

        sections = [[parsed_data]] if isinstance(parsed_data, SingleSection) else parsed_data
        levels = tuple(chain.from_iterable(subsection.levels_iter() for section in sections for subsection in section))
        if levels:
            min_level, max_level = min(levels), max(levels)
        else:
            min_level = max_level = 0

        for section in sections:
            self.append(Section(section, min_level=min_level, max_level=max_level))

        self.length = sum(section.length for section in self)
        self.height = self[0].height


class _GlobalEnvironment(Protocol):
    name: Name
    width: Width
    continuous: Continuous
    time: Time
    delay: Delay
    beat: Beat
    tick: Tick
    trill_style: TrillStyle
    position: GlobalPosition
    instrument: Instrument
    dynamic: Dynamic
    sustain: Sustain
    transpose: Transpose


class _DefaultEnvironment:
    name = Name()
    width = Width()
    continuous = Continuous()
    time = Time()
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
    def __init__(self, index: int, src: T_Section, env: _GlobalEnvironment):
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


class MultiSection(_BaseSection, Iterable["CompoundSection"]):
    def __init__(self, index: int, src: T_MultiSection, env: _GlobalEnvironment):
        super().__init__(index, src, env)
        self.continuous = env.continuous.transform(src.continuous)
        self._sections = (self.subsection(index, src_subsection) for index, src_subsection in enumerate(src.sections))

    def __iter__(self) -> Iterator[CompoundSection]:
        # flatten nested sections,
        # organize into lists of continuous sections (compound sections)
        for subsection in self._sections:
            if isinstance(subsection, SingleSection):
                yield [subsection]
            elif subsection.continuous.resolve():
                yield list(chain(*subsection))
            else:
                yield from subsection

    def subsection(self: _GlobalEnvironment, index: int, src: T_Section) -> SingleSection | MultiSection:
        if isinstance(src, T_SingleDivisionSection):
            return SingleDivisionSection(index, src, self)
        if isinstance(src, T_DoubleDivisionSection):
            return DoubleDivisionSection(index, src, self)
        return MultiSection(index, src, self)


def _process_voices(voices: Iterable[Voice]):
    sequential_notes: list[list[Note]] = []
    # voices are not necesarily of equal length, pad them with empty notes
    for beat in map(chain.from_iterable, zip_longest(*voices, fillvalue=())):
        # step_iter is guaranteed to have at least one element (see _Note.__mul__)
        parallel_notes = [first := next(beat)]
        for note in beat:
            if first.delay != note.delay:
                raise ValueError(f"inconsistent delays: {first}(delay={first.delay}) and {note}(delay={note.delay})")
            if first.where != note.where:
                raise ValueError(f"inconsistent placements: {first} and {note}")
            parallel_notes.append(note)
        sequential_notes.append(parallel_notes)
    return sequential_notes


class SingleDivisionSection(_BaseSection, list[list["SingleDivisionNote"]]):
    def __init__(self, index: int, src: T_SingleDivisionSection, env: _GlobalEnvironment):
        super().__init__(index, src, env)
        voices = multivalue_flatten(
            positional_map(SingleDivisionVoice, i, voice, self)
            for i, voice in enumerate(src.voices)
            if voice is not None
        )
        self += _process_voices(voices)

    def levels_iter(self) -> Iterator[T_LevelIndex]:
        for beat in self:
            for note in beat:
                if (level := note.position) is not None:
                    yield level


class DoubleDivisionSection(_BaseSection, list[list["DoubleDivisionNote"]]):
    def __init__(self, index: int, src: T_DoubleDivisionSection, env: _GlobalEnvironment):
        super().__init__(index, src, env)
        voices = multivalue_flatten(
            positional_map(DoubleDivisionVoice, i, voice, self)
            for i, voice in enumerate(src.voices)
            if voice is not None
        )
        self += _process_voices(voices)

    def levels_iter(self) -> Iterator[T_LevelIndex]:
        for beat in self:
            for note in beat:
                if (level := note.position[1]) is not None:
                    yield level


SingleSection = SingleDivisionSection | DoubleDivisionSection
CompoundSection = list[SingleSection]


class _BaseVoice:
    position: SingleDivisionPosition | DoubleDivisionPosition

    def __init__(self, index: T_LevelIndex, src: T_Voice, env: SingleSection):
        # --- setup env ---
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
        # --- parse notes ---
        self.current_bar = 1  # bar indexing starts from 1
        self.current_beat = 0  # but beat starts from 0
        self._notes = self._resolve_sequential_notes(src.notes)

    def __iter__(self) -> Iterator[Iterable[Note]]:
        yield from self._notes

    def _transform_core(self, src: T_NoteMeta):
        self.time = self.time.transform(src.time)
        self.delay = self.delay.transform(src.delay)
        self.beat = self.beat.transform(src.beat)
        self.trill_style = self.trill_style.transform(src.trill_style)
        self.position = self.position.transform(src.position)
        self.instrument = self.instrument.transform(src.instrument)
        self.dynamic = self.dynamic.transform(src.dynamic)
        self.sustain = self.sustain.transform(src.sustain)
        self.transpose = self.transpose.transform(src.transpose)

    @contextmanager
    def _transform(self, src: T_NoteMeta):
        self_copy = shallowcopy(self)
        self_copy._transform_core(src)  # noqa: SLF001
        try:
            yield self_copy
        finally:
            self.current_bar = self_copy.current_bar
            self.current_beat = self_copy.current_beat

    def _resolve_sequential_notes(self, src: T_SequentialNotes):
        def _resolve_core(note: T_SingleNote | T_ParallelNotes | T_NotesModifier) -> Iterable[Iterable[Note]]:
            if isinstance(note, T_SingleNote):
                return self._resolve_single_note(note)
            if isinstance(note, T_ParallelNotes):
                return self._resolve_parallel_notes(note)
            self._transform_core(note)
            return ()

        with self._transform(src) as self:
            sequential_lines = map(_resolve_core, src.note)
            merged_line = chain.from_iterable(sequential_lines)
            return deque(merged_line)

    def _resolve_parallel_notes(self, src: T_ParallelNotes):
        current_bar, current_beat = self.current_bar, self.current_beat

        def _resolve_core(note: T_SingleNote | T_SequentialNotes) -> Iterable[Iterable[Note]]:
            self.current_bar, self.current_beat = current_bar, current_beat
            if isinstance(note, T_SingleNote):
                return self._resolve_single_note(note)
            return self._resolve_sequential_notes(note)

        with self._transform(src) as self:
            parallel_lines = map(_resolve_core, src.note)
            # fail if parallel lines written by the user are not of the same length # TODO: error handling
            merged_line = map(chain.from_iterable, transpose(parallel_lines))
            return deque(merged_line)

    def _resolve_single_note(self, src: T_SingleNote) -> Iterable[Iterable[Note]]:
        with self._transform(src) as self:
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

    def _parse_note(self, src: T_NoteName | T_Rest) -> tuple[T_Positional[NoteBlock | None], T_Duration]:
        tokens = split_timedvalue(src)
        note_name = tokens[0].lower()
        note_duration = parse_duration(*tokens[1:], beat=self.beat.resolve())
        note = self.instrument.resolve(note_name, transpose=self.transpose.resolve())  # TODO: error handling
        return note, note_duration

    def _create_noteblocks(self, src: T_NoteName | T_Rest) -> Iterable[T_Positional[NoteBlock | None]]:
        note, duration = self._parse_note(src)
        return repeat(note, duration)

    def _resolve_multiple_notes(self, _note: T_MultipleNotes):
        individual_notes = strip_split(_note, ",")
        return deque(chain.from_iterable(map(self._resolve_regular_note, individual_notes)))

    def _resolve_regular_note(self, _note: T_NoteName | T_Rest) -> Iterable[Iterable[Note]]:
        return self._apply_phrasing(*self._create_noteblocks(_note))

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

    def _apply_phrasing(self, *noteblocks: T_Positional[NoteBlock | None]) -> Iterable[Iterable[Note]]:
        note_duration = len(noteblocks)
        time = self.time.resolve()
        beat = self.beat.resolve()
        delay = self.delay.resolve()
        sustain = self.sustain.resolve(beat=beat, note_duration=note_duration)
        position = self.position.resolve(beat=beat, sustain_duration=sustain, note_duration=note_duration)
        dynamic = self.dynamic.resolve(beat=beat, sustain_duration=sustain, note_duration=note_duration)
        current_bar, current_beat = self.current_bar, self.current_beat

        def transform(
            *noteblocks: NoteBlock | None,
            dynamic: Iterable[T_StaticAbsoluteDynamic],
            position: Iterable[T_Index | None],
        ):
            def apply_delay_and_position(noteblocks: Iterable[NoteBlock | None]) -> Iterable[Note]:
                for noteblock, note_position in zip(noteblocks, position, strict=False):
                    yield self._create_note(noteblock=noteblock, delay=delay, position=note_position)
                    if (beat := self.current_beat + 1) < time:
                        self.current_beat = beat
                    else:
                        self.current_beat = 0
                        self.current_bar += 1

            def apply_dynamic(notes: Iterable[Note]) -> Iterable[Iterable[Note]]:
                return map(operator.mul, notes, dynamic)

            self.current_bar, self.current_beat = current_bar, current_beat
            return apply_dynamic(apply_delay_and_position(noteblocks))

        parallel_lines = positional_map(transform, *noteblocks, dynamic=dynamic, position=position)
        if type(parallel_lines) is T_MultiValue:
            merged_line = map(chain.from_iterable, transpose(parallel_lines))
            return deque(merged_line)
        return deque(parallel_lines)

    def _create_note(
        self,
        *,
        noteblock: NoteBlock | None,
        delay: T_Delay,
        position: T_Index | None | tuple[None, None],
    ) -> Note:
        return cast(
            Note,
            _Note(
                noteblock=noteblock,
                delay=delay,
                position=position,
                voice=self.name,
                where=(self.current_bar, self.current_beat),
            ),
        )


class SingleDivisionVoice(_BaseVoice, Iterable[Iterable["SingleDivisionNote"]]):
    def __init__(self, index: T_LevelIndex, src: T_SingleDivisionVoice, env: SingleDivisionSection):
        self.position = SingleDivisionPosition(index)
        super().__init__(index, src, env)


class DoubleDivisionVoice(_BaseVoice, Iterable[Iterable["DoubleDivisionNote"]]):
    def __init__(self, index: T_LevelIndex, src: T_DoubleDivisionVoice, env: DoubleDivisionSection):
        self.position = DoubleDivisionPosition(index)
        super().__init__(index, src, env)


Voice = SingleDivisionVoice | DoubleDivisionVoice


@dataclass(kw_only=True, slots=True)
class _Note:
    # run-time-significant attributes
    noteblock: NoteBlock | None
    delay: T_Delay
    position: T_Index | None | tuple[None, None]
    # ---------------
    voice: str  # for error messages
    where: tuple[int, int]  # for compile-time checks

    def __mul__(self, dynamic: T_StaticAbsoluteDynamic):
        if self.noteblock is None or dynamic == 0:
            dynamic = 1
            # no need to copy, we only __mul__ a freshly-created note
            self.noteblock = None
            if isinstance(self.position, int):
                self.position = None
            elif isinstance(self.position, int):
                self.position = (None, None)
        return repeat(self, dynamic)

    def __repr__(self):
        return f"{self.voice}@{self.where}"


class SingleDivisionNote(Protocol):
    noteblock: NoteBlock | None
    delay: T_Delay
    position: T_LevelIndex | None
    voice: str
    where: tuple[int, int]


class DoubleDivisionNote(Protocol):
    noteblock: NoteBlock | None
    delay: T_Delay
    position: T_DoubleIndex | tuple[None, None]
    voice: str
    where: tuple[int, int]


Note = SingleDivisionNote | DoubleDivisionNote
