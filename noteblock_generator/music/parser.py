from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from copy import copy as shallowcopy
from dataclasses import dataclass
from itertools import chain, repeat
from typing import Iterable, Iterator, Protocol, cast

from .properties import (
    Beat,
    Dynamic,
    Instrument,
    Name,
    NoteBlock,
    P_Named,
    P_Position,
    Position,
    Sustain,
    Tempo,
    Time,
    Transpose,
    TrillStyle,
)
from .utils import (
    MultiSet,
    is_typeform,
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
    T_TickRate,
    T_TrilledNote,
    T_TrillStyle,
    T_Voice,
    Tuple,
)


def parse(validated_data: T_Composition):
    class _DefaultEnvironment:
        children_count = 0
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


class _P_NamedEnvironment(_P_Environment, P_Named, Protocol): ...


class _Environment:
    def __init__(self, index: int | tuple[int, int], src: T_NamedEnvironment, env: _P_NamedEnvironment):
        self.children_count = 0
        env.children_count += 1
        self.name = env.name.transform(index, src, self)
        self.transform(src, env)

    def __hash__(self):
        return id(self)

    def __str__(self):
        return self.name.resolve()

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
        return self._movements


class P_Movement(Iterable["P_Chord"]):
    def __init__(self, index: int, src: T_Movement, env: P_Composition):
        def get_chords() -> Iterator[P_Chord]:
            if isinstance(src, T_Section):
                yield from P_Section(index, src, env)
                return
            for i, subsection in enumerate(src):
                yield from P_Section((index, i), subsection, env)

        self._chords = get_chords()

    def __iter__(self) -> Iterator[P_Chord]:
        return self._chords


class P_Section(_Environment, Iterable["P_Chord"]):
    def __init__(self, index: int | tuple[int, int], src: T_Section, env: P_Composition):
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
        merged_voice = map(chain.from_iterable, transpose(self._voices, fillvalue=()))
        return map(_ChordFactory, merged_voice)


def _ChordFactory(src: Iterator[_Note]) -> P_Chord:
    def _check_index(notes: Tuple[_Note]) -> None:
        first = notes[0]
        for note in notes[1:]:
            if first.index != note.index:
                raise ValueError(f"inconsistent placements: {first} & {note}")

    def _check_tempo(notes: Tuple[_Note]) -> T_TickRate:  # TODO: horrible algorithm
        # Error if different voices conflict,
        # EXCEPT if there are more than two voices, and exactly one voice goes against all others,
        # then that voice's value triumphs.
        # ....
        # The idea is that the lone conflicting voice will be interpreted as the lead voice.
        # This makes it easier to change tempo
        # (only have to change one voice rather than all of them, which would be a huge pain).

        notes_by_tempo = MultiSet(notes, lambda note: note.tempo)
        if len(notes_by_tempo) < 2:
            return next(iter(notes_by_tempo))
        if len(notes_by_tempo) > 2 or len(notes) == 2:
            raise _tempo_error(notes_by_tempo)
        notes_by_tempo_by_voice = {k: MultiSet(v, lambda note: note.voice) for k, v in notes_by_tempo.items()}
        result = min(notes_by_tempo_by_voice, key=lambda tempo: len(notes_by_tempo_by_voice[tempo]))
        if len(notes_by_tempo_by_voice[result]) != 1:
            raise _tempo_error(notes_by_tempo)
        return result

    def _check_time(notes: Tuple[_Note]) -> int:
        # TODO: horrible algorithm
        # TODO: 95% duplicate code with tempo

        notes_by_time = MultiSet(notes, lambda note: note.time)
        if len(notes_by_time) < 2:
            return next(iter(notes_by_time))
        if len(notes_by_time) > 2 or len(notes) == 2:
            raise _time_error(notes_by_time)
        notes_by_time_by_voice = {k: MultiSet(v, lambda note: note.voice) for k, v in notes_by_time.items()}
        result = min(notes_by_time_by_voice, key=lambda time: len(notes_by_time_by_voice[time]))
        if len(notes_by_time_by_voice[result]) != 1:
            raise _time_error(notes_by_time)
        return result

    notes = tuple(src)
    _check_index(notes)
    tempo = _check_tempo(notes)
    time = _check_time(notes)
    notes_by_level = MultiSet(notes, lambda note: note.level)

    # single division
    if all(note.division is None for note in notes):
        for level in range(0, min(notes_by_level) - 1, -1):
            notes = notes_by_level.get(level, ())
            yield P_Unit(notes, tempo=tempo, time=time)
        return

    # double division
    for level in range(0, min(notes_by_level) - 1, -1):
        level_notes = notes_by_level.get(level, ())
        level_notes_by_division = MultiSet(level_notes, lambda note: note.division)

        bothsides_notes = level_notes_by_division.get(None, ())
        left_notes = chain(level_notes_by_division.get(0, ()), bothsides_notes)
        right_notes = chain(level_notes_by_division.get(1, ()), bothsides_notes)

        left_unit = P_Unit(left_notes, tempo=tempo, time=time)
        right_unit = P_Unit(right_notes, tempo=tempo, time=time)
        yield (left_unit, right_unit)


class P_Unit(Iterable[NoteBlock]):
    def __init__(self, notes: Iterable[_Note], *, tempo: T_TickRate, time: int):
        non_empty_notes = [note for note in notes if note.noteblock is not None]
        if len(non_empty_notes) > Dynamic.MAX:
            level = non_empty_notes[0].level
            raise ValueError(f"Slot overflow at {level}: {non_empty_notes}")
        self.tempo = tempo
        self.time = time
        self._noteblocks = cast(list[NoteBlock], [note.noteblock for note in non_empty_notes])

    def __iter__(self) -> Iterator[NoteBlock]:
        yield from self._noteblocks

    def __bool__(self):
        return bool(self._noteblocks)


P_SingleChord = Iterable[P_Unit]
P_DoubleChord = Iterable[tuple[P_Unit, P_Unit]]
P_Chord = P_SingleChord | P_DoubleChord


def _tempo_error(notes_by_tempo: MultiSet[T_TickRate, _Note]):
    it = iter(notes_by_tempo.items())
    t1, note1 = next(it)
    t2, note2 = next(it)
    return ValueError(f"inconsistent tempi: {note1}(tempo={t1}) & {note2}(tempo={t2})")


def _time_error(notes_by_time: MultiSet[int, _Note]):
    it = iter(notes_by_time.items())
    t1, note1 = next(it)
    t2, note2 = next(it)
    return ValueError(f"inconsistent times: {note1}(tempo={t1}) & {note2}(tempo={t2})")


class _Voice(_Environment, Iterable[Iterable["_Note"]]):
    def __init__(self, index: int | tuple[int, int], src: T_Voice, env: P_Section):
        super().__init__(index, src, env)
        # --- anchor ---
        # meaning, if a note `$reset`s a property, it will be reset to thisl value
        self.time.anchor()
        self.tempo.anchor()
        self.beat.anchor()
        self.trill_style.anchor()
        level_index = index if isinstance(index, int) else index[0]
        self.position.anchor(-level_index)  # flip order: lower index is higher position
        self.instrument.anchor()
        self.dynamic.anchor()
        self.sustain.anchor()
        self.transpose.anchor()
        # --- parse ---
        self.i_bar = 1  # bar indexing starts from 1
        self.i_tick = 0  # but tick starts from 0
        self._notes = self._resolve_sequential_notes(src)

    def __iter__(self) -> Iterator[Iterable[_Note]]:
        return self._notes

    @contextmanager
    def local_transform(self, src: T_NoteMeta):
        self_copy = shallowcopy(self)
        self_copy.transform(src, self)
        try:
            yield self_copy
        finally:
            self.i_bar = self_copy.i_bar
            self.i_tick = self_copy.i_tick

    def _resolve_sequential_notes(self, src: T_SequentialNotes) -> Iterator[Iterable[_Note]]:
        def _resolve_core(note: T_SingleNote | T_ParallelNotes | T_NotesModifier) -> Iterable[Iterable[_Note]]:
            if isinstance(note, T_SingleNote):
                return self._resolve_single_note(note)
            if isinstance(note, T_ParallelNotes):
                return self._resolve_parallel_notes(note)
            self.transform(note, self)
            return ()

        with self.local_transform(src) as self:
            sequential_lines = map(_resolve_core, src)
            merged_line = chain.from_iterable(sequential_lines)
            return merged_line

    def _resolve_parallel_notes(self, src: T_ParallelNotes) -> Iterable[Iterable[_Note]]:
        i_bar, i_tick = self.i_bar, self.i_tick

        def resolve_core(note: T_SingleNote | T_SequentialNotes) -> Iterable[Iterable[_Note]]:
            self.i_bar, self.i_tick = i_bar, i_tick
            if isinstance(note, T_SingleNote):
                return self._resolve_single_note(note)
            return self._resolve_sequential_notes(note)

        def check_tempo(notes: Iterable[_Note]) -> Iterator[_Note]:
            notes_by_tempo = MultiSet(notes, lambda note: note.tempo)
            if len(notes_by_tempo) < 2:
                return notes_by_tempo.flatten()
            raise _tempo_error(notes_by_tempo)

        def check_time(notes: Iterable[_Note]) -> Iterator[_Note]:
            notes_by_time = MultiSet(notes, lambda note: note.time)
            if len(notes_by_time) < 2:
                return notes_by_time.flatten()
            raise _time_error(notes_by_time)

        with self.local_transform(src) as self:
            parallel_lines = map(resolve_core, src.note)
            merged_line = map(chain.from_iterable, transpose(parallel_lines, fillvalue=()))
            return map(check_time, map(check_tempo, merged_line))

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
        note = self.instrument.resolve(note_name=note_name, transpose=self.transpose.resolve())
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

        def create_note(noteblock: NoteBlock | None, position: P_Position):
            return _Note(
                noteblock=noteblock,
                tempo=tempo,
                time=time,
                position=position,
                voice=self,
                index=(self.i_bar, self.i_tick),
            )

        def transform(
            *noteblocks: NoteBlock | None,
            dynamic: Iterable[T_StaticAbsoluteDynamic],
            position: Iterable[P_Position],
        ):
            def apply_position(noteblocks: Iterable[NoteBlock | None]) -> Iterable[_Note]:
                for noteblock, note_position in zip(noteblocks, position):
                    yield create_note(noteblock=noteblock, position=note_position)
                    if (tick := self.i_tick + 1) < time:
                        self.i_tick = tick
                    else:
                        self.i_tick = 0
                        self.i_bar += 1

            def apply_dynamic(notes: Iterable[_Note]) -> Iterable[Iterable[_Note]]:
                def apply_core(note: _Note, dynamic: T_StaticAbsoluteDynamic) -> Iterable[_Note]:
                    if note.noteblock is None:
                        return (note,)
                    if dynamic == 0:
                        note.noteblock = None
                        return (note,)
                    return repeat(note, dynamic)

                return map(apply_core, notes, dynamic)

            self.i_bar, self.i_tick = i_bar, i_tick
            return apply_dynamic(apply_position(noteblocks))

        parallel_lines = multivalue_map(transform, *noteblocks, dynamic=dynamic, position=position)
        if type(parallel_lines) is T_MultiValue:
            # no fillvalue needed, by design this transposition should never fail
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
    position: P_Position
    # for error checking only
    voice: _Voice
    index: tuple[T_Bar, T_Tick]

    @property
    def division(self):
        return self.position[0]

    @property
    def level(self):
        return self.position[1]

    def __repr__(self):
        return f"{self.voice}{self.index}"
