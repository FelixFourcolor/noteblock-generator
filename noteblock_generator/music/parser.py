from __future__ import annotations

import operator
from collections import deque
from contextlib import contextmanager
from copy import copy as shallowcopy
from dataclasses import dataclass
from itertools import chain, repeat, zip_longest
from typing import Iterable, Iterator, Literal, Protocol

from .properties import (
    Beat,
    Dynamic,
    Instrument,
    Name,
    NoteBlock,
    Position,
    Sustain,
    T_LevelIndex,
    T_PositionIndex,
    Tempo,
    Time,
    Transpose,
    TrillStyle,
)
from .utils import (
    is_typeform,
    multivalue_flatten,
    multivalue_map,
    parse_duration,
    split_timedvalue,
    strip_split,
    transpose,
)
from .validator import (
    T_BarDelimiter,
    T_Composition,
    T_CompoundNote,
    T_Duration,
    T_Environment,
    T_Movement,
    T_MultipleNotes,
    T_MultiValue,
    T_NamedEnvironment,
    T_NoteMeta,
    T_NoteName,
    T_NotesModifier,
    T_ParallelNotes,
    T_Positional,
    T_Rest,
    T_Section,
    T_SequentialNotes,
    T_SingleNote,
    T_StaticAbsoluteDynamic,
    T_TrilledNote,
    T_TrillStyle,
    T_Voice,
)


def parse(validated_data: T_Composition):
    class _DefaultEnvironment:
        name = Name()
        time = Time()
        beat = Beat()
        tempo = Tempo()
        trill_style = TrillStyle()
        position = Position()
        instrument = Instrument()
        dynamic = Dynamic()
        sustain = Sustain()
        transpose = Transpose()

    return Composition(0, validated_data, _DefaultEnvironment)  # TODO: error handling


T_Bar = T_Tick = int


@dataclass(kw_only=True, slots=True)
class Note:
    # run-time-significant attributes
    noteblock: NoteBlock | None
    tempo: float
    time: int
    position: T_PositionIndex
    # for error checking only
    voice: str
    index: tuple[T_Bar, T_Tick]

    @property
    def division(self):
        if self.position is not None:
            return self.position[0]

    @property
    def level(self):
        if self.position is not None:
            return self.position[1]

    def __mul__(self, dynamic: T_StaticAbsoluteDynamic):
        if self.noteblock is None or dynamic == 0:
            dynamic = 1
            # no need to copy, we only __mul__ a freshly-created note
            self.noteblock = self.position = None
        return repeat(self, dynamic)

    def __repr__(self):
        return f"{self.voice}@{self.index}"


class Chord(list[Note]):
    type: Literal["single", "double", None]
    time: int
    tempo: float

    def __init__(self, src: Iterator[Note]):
        first = next(src)  # every chord is guaranteed to have at least one note (see Note.__mul__)
        self.append(first)
        for note in src:
            if first.index != note.index:
                raise ValueError(f"inconsistent placements: {first} & {note}")
            self.append(note)

        self._check_position()
        self._check_time()
        self._check_tempo()

    def _check_position(self):
        if all(note.position is None for note in self):
            self.type = None
        elif all(is_typeform(note.position, tuple[None, T_LevelIndex]) for note in self):
            self.type = "single"
        else:
            self.type = "double"
            for note in self[:]:
                if is_typeform(note.position, tuple[None, T_LevelIndex]):
                    copy = shallowcopy(note)
                    level = note.position[1]
                    note.position = (0, level)
                    copy.position = (1, level)
                    self.append(copy)

    def _check_time(self):
        times: dict[int, list[Note]] = {}
        for note in self:
            if note.time not in times:
                times[note.time] = [note]
            else:
                times[note.time].append(note)

        def time_error():
            it = iter(times.values())
            note1 = next(it)[0]
            note2 = next(it)[0]
            t1, t2 = note1.time, note2.time
            return ValueError(f"inconsistent time signatures: {note1}(time={t1}) & {note2}(time={t2})")

        if len(times) > 2:
            raise time_error()
        if len(times) == 2:
            if len(self) == 2:
                raise time_error()
            self.time = min(times, key=lambda x: len(times[x]))
            if len(times[self.time]) != 1:
                raise time_error()
        else:
            self.time = next(iter(times))

    def _check_tempo(self):
        tempi: dict[float, list[Note]] = {}
        for note in self:
            if note.tempo not in tempi:
                tempi[note.tempo] = [note]
            else:
                tempi[note.tempo].append(note)

        def tempo_error():
            it = iter(tempi.values())
            note1 = next(it)[0]
            note2 = next(it)[0]
            t1, t2 = note1.tempo, note2.tempo
            return ValueError(f"inconsistent tempi: {note1}(tempo={t1}) & {note2}(tempo={t2})")

        if len(tempi) > 2:
            raise tempo_error()
        if len(tempi) == 2:
            if len(self) == 2:
                raise tempo_error()
            self.tempo = min(tempi, key=lambda x: len(tempi[x]))
            if len(tempi[self.tempo]) != 1:
                raise tempo_error()
        else:
            self.tempo = next(iter(tempi))


class _Environment(Protocol):
    time: Time
    tempo: Tempo
    beat: Beat
    trill_style: TrillStyle
    position: Position
    instrument: Instrument
    dynamic: Dynamic
    sustain: Sustain
    transpose: Transpose


class _NamedEnvironment(_Environment, Protocol):
    name: Name


class _BaseEnvironment:
    def __init__(self, index: int | tuple[int, int], src: T_NamedEnvironment, env: _NamedEnvironment):
        self.name = env.name.transform(index, src)
        self.transform(src, env)

    def transform(self, src: T_Environment, env: _Environment):
        self.time = env.time.transform(src.time)
        self.tempo = env.tempo.transform(src.tempo)
        self.beat = env.beat.transform(src.beat)
        self.trill_style = env.trill_style.transform(src.trill_style)
        self.position = env.position.transform(src.position)
        self.instrument = env.instrument.transform(src.instrument)
        self.dynamic = env.dynamic.transform(src.dynamic)
        self.sustain = env.sustain.transform(src.sustain)
        self.transpose = env.transpose.transform(src.transpose)


class Section(_BaseEnvironment, list[Chord]):
    def __init__(self, index: int | tuple[int, int], src: T_Section, env: _NamedEnvironment):
        super().__init__(index, src, env)
        voices = multivalue_flatten(
            multivalue_map(Voice, i, voice, self)  #
            for i, voice in enumerate(src)
            if voice is not None
        )
        # voices are not necesarily of equal length, pad them with empty notes
        merged_voice = map(chain.from_iterable, zip_longest(*voices, fillvalue=()))
        self += map(Chord, merged_voice)

    def level_iter(self) -> Iterator[T_LevelIndex]:
        for chord in self:
            for note in chord:
                if (level := note.level) is not None:
                    yield level


class Movement(list[Section]):
    def __init__(self, index: int, src: T_Movement, env: _NamedEnvironment):
        if isinstance(src, T_Section):
            self.append(Section(index, src, env))
        else:
            for i, subsection in enumerate(src):
                self += Section((index, i), subsection, env)


class Composition(_BaseEnvironment, list[Movement]):
    def __init__(self, base_index: int, src: T_Composition, env: _NamedEnvironment):
        super().__init__(base_index, src, env)
        self.current_index = 0
        for movement in src:
            if isinstance(movement, T_Composition):
                subsection = Composition(base_index + self.current_index, movement, self)
                self += subsection
                self.current_index = subsection.current_index
            else:
                self.append(Movement(base_index + self.current_index, movement, self))
                self.current_index += 1


class Voice(_BaseEnvironment):
    def __init__(self, index: T_LevelIndex, src: T_Voice, env: _NamedEnvironment):
        super().__init__(index, src, env)
        self.position = env.position.anchor(index).transform(src.position, save=True)
        self._str = self.name.resolve()
        # --- parse notes ---
        self.current_bar = 1  # bar indexing starts from 1
        self.current_tick = 0  # but tick starts from 0
        self._notes = self._resolve_sequential_notes(src)

    def __str__(self):
        return self._str

    def __iter__(self) -> Iterator[Iterable[Note]]:
        yield from self._notes

    @contextmanager
    def local_transform(self, src: T_NoteMeta):
        self_copy = shallowcopy(self)
        self_copy.transform(src, self)
        try:
            yield self_copy
        finally:
            self.current_bar = self_copy.current_bar
            self.current_tick = self_copy.current_tick

    def _resolve_sequential_notes(self, src: T_SequentialNotes):
        def _resolve_core(note: T_SingleNote | T_ParallelNotes | T_NotesModifier) -> Iterable[Iterable[Note]]:
            if isinstance(note, T_SingleNote):
                return self._resolve_single_note(note)
            if isinstance(note, T_ParallelNotes):
                return self._resolve_parallel_notes(note)
            self.transform(note, self)
            return ()

        with self.local_transform(src) as self:
            sequential_lines = map(_resolve_core, src.note)
            merged_line = chain.from_iterable(sequential_lines)
            return deque(merged_line)

    def _resolve_parallel_notes(self, src: T_ParallelNotes):
        current_bar, current_tick = self.current_bar, self.current_tick

        def _resolve_core(note: T_SingleNote | T_SequentialNotes) -> Iterable[Iterable[Note]]:
            self.current_bar, self.current_tick = current_bar, current_tick
            if isinstance(note, T_SingleNote):
                return self._resolve_single_note(note)
            return self._resolve_sequential_notes(note)

        with self.local_transform(src) as self:
            parallel_lines = map(_resolve_core, src.note)
            # TODO: error handling: fail if parallel lines written by the user are not of the same length
            merged_line = map(chain.from_iterable, transpose(parallel_lines))
            return deque(merged_line)

    def _resolve_single_note(self, src: T_SingleNote) -> Iterable[Iterable[Note]]:
        with self.local_transform(src) as self:
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
            self.current_tick = 0
            self.current_bar = asserted_bar_number
        elif self.current_tick != 0:
            raise ValueError("wrong barline location")
        elif self.current_bar != asserted_bar_number:
            raise ValueError("wrong bar number")

        if rest:
            beat = self.beat.resolve()
            time = self.time.resolve(beat=beat)
            return self._resolve_regular_note(f"r {time}")
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
        # if a trill only lasted one tick, it wouldn't be a trill,
        # unless the main note also lasts only one tick
        trill_duration = max(trill_duration, min(note_duration, 2))

        place_trill_here = (lambda i: i % 2 == 0) if trill_style == "alt" else (lambda i: i % 2 == 1)
        for i in range(trill_duration):
            if place_trill_here(i):
                noteblocks[i] = trill_noteblock
        return self._apply_phrasing(*noteblocks)

    def _apply_phrasing(self, *noteblocks: T_Positional[NoteBlock | None]) -> Iterable[Iterable[Note]]:
        note_duration = len(noteblocks)
        beat = self.beat.resolve()
        time = self.time.resolve(beat=beat)
        tempo = self.tempo.resolve(beat=beat)
        sustain = self.sustain.resolve(beat=beat, note_duration=note_duration)
        position = self.position.resolve(beat=beat, sustain_duration=sustain, note_duration=note_duration)
        dynamic = self.dynamic.resolve(beat=beat, sustain_duration=sustain, note_duration=note_duration)
        current_bar, current_tick = self.current_bar, self.current_tick

        def create_note(noteblock: NoteBlock | None, position: T_PositionIndex):
            return Note(
                noteblock=noteblock,
                tempo=tempo,
                time=time,
                position=position,
                voice=str(self),
                index=(self.current_bar, self.current_tick),
            )

        def transform(
            *noteblocks: NoteBlock | None,
            dynamic: Iterable[T_StaticAbsoluteDynamic],
            position: Iterable[T_PositionIndex],
        ):
            def apply_position(noteblocks: Iterable[NoteBlock | None]) -> Iterable[Note]:
                for noteblock, note_position in zip(noteblocks, position, strict=False):
                    yield create_note(noteblock=noteblock, position=note_position)
                    if (tick := self.current_tick + 1) < time:
                        self.current_tick = tick
                    else:
                        self.current_tick = 0
                        self.current_bar += 1

            def apply_dynamic(notes: Iterable[Note]) -> Iterable[Iterable[Note]]:
                return map(operator.mul, notes, dynamic)

            self.current_bar, self.current_tick = current_bar, current_tick
            return apply_dynamic(apply_position(noteblocks))

        parallel_lines = multivalue_map(transform, *noteblocks, dynamic=dynamic, position=position)
        if type(parallel_lines) is T_MultiValue:
            merged_line = map(chain.from_iterable, transpose(parallel_lines))
            return deque(merged_line)
        return deque(parallel_lines)
