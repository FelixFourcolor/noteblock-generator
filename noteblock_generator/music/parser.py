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
from .utils import is_typeform, multivalue_map, parse_duration, split_timedvalue, strip_split, transpose
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
    T_TickRate,
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

    return P_Composition(0, validated_data, _DefaultEnvironment)  # TODO: error handling


class _P_Environment(Protocol):
    time: Time
    tempo: Tempo
    beat: Beat
    trill_style: TrillStyle
    position: Position
    instrument: Instrument
    dynamic: Dynamic
    sustain: Sustain
    transpose: Transpose


class _P_NamedEnvironment(_P_Environment, Protocol):
    name: Name


class _Environment:
    def __init__(self, index: int | tuple[int, int], src: T_NamedEnvironment, env: _P_NamedEnvironment):
        self.name = env.name.transform(index, src)
        self.transform(src, env)

    def transform(self, src: T_Environment, env: _P_Environment):
        self.time = env.time.transform(src.time)
        self.tempo = env.tempo.transform(src.tempo)
        self.beat = env.beat.transform(src.beat)
        self.trill_style = env.trill_style.transform(src.trill_style)
        self.position = env.position.transform(src.position)
        self.instrument = env.instrument.transform(src.instrument)
        self.dynamic = env.dynamic.transform(src.dynamic)
        self.sustain = env.sustain.transform(src.sustain)
        self.transpose = env.transpose.transform(src.transpose)


class P_Composition(_Environment, Iterable["P_Movement"]):
    def __init__(self, index: int, src: T_Composition, env: _P_NamedEnvironment):
        super().__init__(index, src, env)

        self.i_index = 0

        def get_movements() -> Iterator[P_Movement]:
            for movement in src:
                if isinstance(movement, T_Composition):
                    subsection = P_Composition(index + self.i_index, movement, self)
                    yield from subsection
                    self.i_index = subsection.i_index
                else:
                    yield P_Movement(index + self.i_index, movement, self)
                    self.i_index += 1

        self._movements = get_movements()

    def __iter__(self) -> Iterator[P_Movement]:
        yield from self._movements


class P_Movement(Iterable["P_Chord"]):
    def __init__(self, index: int, src: T_Movement, env: _P_NamedEnvironment):
        def get_chords() -> Iterator[P_Chord]:
            if isinstance(src, T_Section):
                yield from P_Section(index, src, env)
            else:
                for i, subsection in enumerate(src):
                    yield from P_Section((index, i), subsection, env)

        self._chords = get_chords()

    def __iter__(self) -> Iterator[P_Chord]:
        yield from self._chords


class P_Section(_Environment, Iterable["P_Chord"]):
    def __init__(self, index: int | tuple[int, int], src: T_Section, env: _P_NamedEnvironment):
        super().__init__(index, src, env)

        def get_voices() -> Iterator[_Voice]:
            for i, sub_src in enumerate(src):
                if isinstance(sub_src, T_Voice):
                    yield _Voice(i, sub_src, self)
                elif sub_src is not None:
                    for j, voice in enumerate(sub_src):
                        yield _Voice((i, j), voice, self)

        self._voices = get_voices()

    def __iter__(self) -> Iterator[P_Chord]:
        # voices are not necesarily of equal length, pad them with empty notes
        merged_voice = map(chain.from_iterable, zip_longest(*self._voices, fillvalue=()))
        yield from map(_ChordFactory, merged_voice)


class _Voice(_Environment, Iterable[Iterable["_Note"]]):
    def __init__(self, index: int | tuple[int, int], src: T_Voice, env: _P_NamedEnvironment):
        super().__init__(index, src, env)
        self._str = self.name.resolve()
        # --- anchor ---
        # meaning, if a note "$reset" a property, it will be reset to this current value
        self.time.anchor()
        self.tempo.anchor()
        self.beat.anchor()
        self.trill_style.anchor()
        self.position.anchor(index if isinstance(index, int) else index[0])
        self.instrument.anchor()
        self.dynamic.anchor()
        self.sustain.anchor()
        self.transpose.anchor()
        # --- parse ---
        self.i_bar = 1  # bar indexing starts from 1
        self.i_tick = 0  # but tick starts from 0
        self._notes = self._resolve_sequential_notes(src)

    def __str__(self):
        return self._str

    def __iter__(self) -> Iterator[Iterable[_Note]]:
        yield from self._notes

    @contextmanager
    def local_transform(self, src: T_NoteMeta):
        self_copy = shallowcopy(self)
        self_copy.transform(src, self)
        try:
            yield self_copy
        finally:
            self.i_bar = self_copy.i_bar
            self.i_tick = self_copy.i_tick

    def _resolve_sequential_notes(self, src: T_SequentialNotes):
        def _resolve_core(note: T_SingleNote | T_ParallelNotes | T_NotesModifier) -> Iterable[Iterable[_Note]]:
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
        i_bar, i_tick = self.i_bar, self.i_tick

        def _resolve_core(note: T_SingleNote | T_SequentialNotes) -> Iterable[Iterable[_Note]]:
            self.i_bar, self.i_tick = i_bar, i_tick
            if isinstance(note, T_SingleNote):
                return self._resolve_single_note(note)
            return self._resolve_sequential_notes(note)

        with self.local_transform(src) as self:
            parallel_lines = map(_resolve_core, src.note)
            # TODO: error handling: fail if parallel lines written by the user are not of the same length
            merged_line = map(chain.from_iterable, transpose(parallel_lines))
            return deque(merged_line)

    def _resolve_single_note(self, src: T_SingleNote) -> Iterable[Iterable[_Note]]:
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

    def _resolve_bar_delimiter(self, src: T_BarDelimiter) -> Iterable[Iterable[_Note]]:
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
            self.i_tick = 0
            self.i_bar = asserted_bar_number
        elif self.i_tick != 0:
            raise ValueError("wrong barline location")
        elif self.i_bar != asserted_bar_number:
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
        note = self.instrument.resolve(note_name=note_name, transpose=self.transpose.resolve())  # TODO: error handling
        return note, note_duration

    def _create_noteblocks(self, src: T_NoteName | T_Rest) -> Iterable[T_Positional[NoteBlock | None]]:
        note, duration = self._parse_note(src)
        return repeat(note, duration)

    def _resolve_multiple_notes(self, _note: T_MultipleNotes):
        individual_notes = strip_split(_note, ",")
        return deque(chain.from_iterable(map(self._resolve_regular_note, individual_notes)))

    def _resolve_regular_note(self, _note: T_NoteName | T_Rest) -> Iterable[Iterable[_Note]]:
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

    def _apply_phrasing(self, *noteblocks: T_Positional[NoteBlock | None]) -> Iterable[Iterable[_Note]]:
        note_duration = len(noteblocks)
        beat = self.beat.resolve()
        time = self.time.resolve(beat=beat)
        tempo = self.tempo.resolve(beat=beat)
        sustain = self.sustain.resolve(beat=beat, note_duration=note_duration)
        position = self.position.resolve(beat=beat, sustain_duration=sustain, note_duration=note_duration)
        dynamic = self.dynamic.resolve(beat=beat, sustain_duration=sustain, note_duration=note_duration)
        i_bar, i_tick = self.i_bar, self.i_tick

        def create_note(noteblock: NoteBlock | None, position: T_PositionIndex):
            return _Note(
                noteblock=noteblock,
                tempo=tempo,
                time=time,
                position=position,
                voice=str(self),
                index=(self.i_bar, self.i_tick),
            )

        def transform(
            *noteblocks: NoteBlock | None,
            dynamic: Iterable[T_StaticAbsoluteDynamic],
            position: Iterable[T_PositionIndex],
        ):
            def apply_position(noteblocks: Iterable[NoteBlock | None]) -> Iterable[_Note]:
                for noteblock, note_position in zip(noteblocks, position, strict=False):
                    yield create_note(noteblock=noteblock, position=note_position)
                    if (tick := self.i_tick + 1) < time:
                        self.i_tick = tick
                    else:
                        self.i_tick = 0
                        self.i_bar += 1

            def apply_dynamic(notes: Iterable[_Note]) -> Iterable[Iterable[_Note]]:
                return map(operator.mul, notes, dynamic)

            self.i_bar, self.i_tick = i_bar, i_tick
            return apply_dynamic(apply_position(noteblocks))

        parallel_lines = multivalue_map(transform, *noteblocks, dynamic=dynamic, position=position)
        if type(parallel_lines) is T_MultiValue:
            merged_line = map(chain.from_iterable, transpose(parallel_lines))
            return deque(merged_line)
        return deque(parallel_lines)


T_Bar = T_Tick = int


@dataclass(kw_only=True, slots=True)
class _Note:
    # run-time-significant attributes
    noteblock: NoteBlock | None
    tempo: T_TickRate
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


class _ChordFactory:
    def __new__(cls, src: Iterator[_Note]) -> P_Chord:
        notes = list(src)
        cls.check_index(notes)
        tempo = cls.check_tempo(notes)
        time = cls.check_time(notes)
        note_type = cls.check_position(notes)

        if note_type == "single":
            return P_SingleChord(
                notes,  # pyright: ignore[reportGeneralTypeIssues]
                tempo=tempo,
                time=time,
            )
        if note_type == "double":
            return P_DoubleChord(
                notes,  # pyright: ignore[reportGeneralTypeIssues]
                tempo=tempo,
                time=time,
            )
        return P_Rest(tempo=tempo, time=time)

    @classmethod
    def check_index(cls, notes: list[_Note]):
        first = notes[0]  # every chord is guaranteed to have at least one note (see _Note.__mul__)
        for note in notes[1:]:
            if first.index != note.index:
                raise ValueError(f"inconsistent placements: {first} & {note}")

    @classmethod
    def check_position(cls, notes: list[_Note]):
        def clear_empty_notes():
            for i, note in enumerate(notes):
                if note.position is None:
                    notes.pop(i)

        clear_empty_notes()
        if not notes:
            return None
        if all(note.division is None for note in notes):
            return "single"
        for note in notes[:]:
            assert note.position is not None  # because of clear_empty_notes()
            division, level = note.position
            if division is None:
                copy = shallowcopy(note)
                note.position = (0, level)
                copy.position = (1, level)
                notes.append(copy)
        return "double"

    @classmethod
    def check_tempo(cls, notes: list[_Note]) -> T_TickRate:
        tempi: dict[T_TickRate, list[_Note]] = {}
        for note in notes:
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
            if len(notes) == 2:
                raise tempo_error()
            tempo = min(tempi, key=lambda x: len(tempi[x]))
            if len(tempi[tempo]) != 1:
                raise tempo_error()
            return tempo
        return next(iter(tempi))

    @classmethod
    def check_time(cls, notes: list[_Note]) -> int:
        times: dict[int, list[_Note]] = {}
        for note in notes:
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
            if len(notes) == 2:
                raise time_error()
            time = min(times, key=lambda x: len(times[x]))
            if len(times[time]) != 1:
                raise time_error()
            return time
        return next(iter(times))


class P_SingleChord(list["P_SingleNote"]):
    def __init__(self, notes: Iterable[P_SingleNote], *, tempo: T_TickRate, time: int):
        self.extend(notes)
        self.tempo = tempo
        self.time = time


class P_DoubleChord(list["P_DoubleNote"]):
    def __init__(self, notes: Iterable[P_DoubleNote], *, tempo: T_TickRate, time: int):
        self.extend(notes)
        self.tempo = tempo
        self.time = time


class P_Rest(list["P_RestNote"]):
    def __init__(self, tempo: T_TickRate, time: int):
        self.tempo = tempo
        self.time = time


P_Chord = P_Rest | P_SingleChord | P_DoubleChord


class _P_BaseNote(Protocol):
    @property
    def tempo(self) -> T_TickRate: ...

    @property
    def time(self) -> int: ...


class P_SingleNote(_P_BaseNote, Protocol):
    @property
    def noteblock(self) -> NoteBlock: ...

    @property
    def division(self) -> None: ...

    @property
    def level(self) -> T_LevelIndex: ...


class P_DoubleNote(_P_BaseNote, Protocol):
    @property
    def noteblock(self) -> NoteBlock: ...

    @property
    def division(self) -> Literal[0, 1]: ...

    @property
    def level(self) -> T_LevelIndex: ...


class P_RestNote(_P_BaseNote, Protocol):
    @property
    def noteblock(self) -> None: ...

    @property
    def division(self) -> None: ...

    @property
    def level(self) -> None: ...
