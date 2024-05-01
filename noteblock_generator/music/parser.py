from __future__ import annotations

import operator
from collections import deque
from contextlib import contextmanager
from copy import copy as shallowcopy
from dataclasses import dataclass
from itertools import chain, repeat, zip_longest
from typing import Iterable, Iterator, Literal, Protocol, overload

from .properties import (
    Beat,
    Delay,
    Dynamic,
    Instrument,
    Name,
    NoteBlock,
    Position,
    Sustain,
    T_LevelIndex,
    T_PositionIndex,
    Tick,
    Time,
    Transpose,
    TrillStyle,
    Width,
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
    T_CompoundNote,
    T_CompoundSection,
    T_Delay,
    T_Duration,
    T_MultipleNotes,
    T_MultiSection,
    T_MultiValue,
    T_NoteMeta,
    T_NoteName,
    T_NotesModifier,
    T_ParallelNotes,
    T_Positional,
    T_Rest,
    T_SequentialNotes,
    T_SingleNote,
    T_SingleSection,
    T_StaticAbsoluteDynamic,
    T_TrilledNote,
    T_TrillStyle,
    T_Voice,
)


def parse(validated_data: T_MultiSection):
    class _DefaultEnvironment:
        name = Name()
        width = Width()
        time = Time()
        delay = Delay()
        beat = Beat()
        tick = Tick()
        trill_style = TrillStyle()
        position = Position()
        instrument = Instrument()
        dynamic = Dynamic()
        sustain = Sustain()
        transpose = Transpose()

    return MultiSection(0, validated_data, _DefaultEnvironment)  # TODO: error handling


@dataclass(kw_only=True, slots=True)
class Note:
    # run-time-significant attributes
    noteblock: NoteBlock | None
    delay: T_Delay
    position: T_PositionIndex
    # for error message only
    voice: str
    where: tuple[int, int]

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
        return f"{self.voice}@{self.where}"


class Chord(list[Note]):
    def __init__(self, src: Iterator[Note]):
        first = next(src)  # every chord is guaranteed to have at least one note (see _Note.__mul__)
        self.append(first)
        self.delay = first.delay
        for note in src:
            if first.where != note.where:
                raise ValueError(f"inconsistent placements: {first} & {note}")
            if self.delay < note.delay:
                self.delay = note.delay
            self.append(note)

        if all(note.position is None for note in self):
            self.type: Literal["single", "double", None] = None
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


class _Environment(Protocol):
    name: Name
    width: Width
    time: Time
    delay: Delay
    beat: Beat
    tick: Tick
    trill_style: TrillStyle
    position: Position
    instrument: Instrument
    dynamic: Dynamic
    sustain: Sustain
    transpose: Transpose


class _BaseSection:
    def __init__(self, index: int | tuple[int, int], src: T_SingleSection | T_MultiSection, env: _Environment):
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


class SingleSection(_BaseSection, list[Chord]):
    def __init__(self, index: int | tuple[int, int], src: T_SingleSection, env: _Environment):
        super().__init__(index, src, env)
        voices = multivalue_flatten(
            multivalue_map(Voice, i, voice, self)  #
            for i, voice in enumerate(src.voices)
            if voice is not None
        )
        # voices are not necesarily of equal length, pad them with empty notes
        merged_voice = map(chain.from_iterable, zip_longest(*voices, fillvalue=()))
        self += map(Chord, merged_voice)

    @overload
    def __getitem__(self, key: int) -> Chord: ...
    @overload
    def __getitem__(self, key: slice) -> SingleSection: ...
    def __getitem__(self, key: int | slice) -> Chord | SingleSection:
        if isinstance(key, int):
            return super().__getitem__(key)

        assert key.step is None
        out = shallowcopy(self)
        if key.start is not None:
            del out[: key.start]
        if key.stop is not None:
            del out[key.stop :]
        return out

    def split(self, index: int) -> SingleSection:
        other = shallowcopy(self)
        del self[:index]
        del other[index:]
        return other

    @property
    def type(self):
        for chord in self:
            if typ := chord.type:
                return typ
        raise Exception("not happening")

    def level_iter(self) -> Iterator[T_LevelIndex]:
        for chord in self:
            for note in chord:
                if (level := note.level) is not None:
                    yield level


class CompoundSection(list[SingleSection]):
    def __init__(self, index: int, src: T_CompoundSection, env: _Environment):
        if isinstance(src, T_SingleSection):
            self.append(SingleSection(index, src, env))
        else:
            for i, subsection in enumerate(src):
                self._merge(SingleSection((index, i), subsection, env))

    def _merge(self, section: SingleSection):
        subsections = self._split(section)

        if len(self) == 0:
            self += subsections
            return

        before = self[-1]
        after = subsections.pop(0)
        if (
            before.width != after.width
            or before.tick != after.tick
            or None is not before.type != after.type is not None
        ):  # if before and after are imcompatible
            self.append(after)  # add a new subsection
        else:
            before.extend(after)  # otherwise extend the previous one
        self += subsections

    def _split(self, section: SingleSection):
        def _split_core(section: SingleSection, *, index__: int) -> list[SingleSection]:
            out = [section]

            if len(section) < 2:
                return out

            if len(section) == 2:
                if None is not section[0].type != section[1].type is not None:
                    out.append(section.split(1))
                return out

            before, this, after = section[:3]
            index__ += 1
            if None is not before.type != this.type is not None:
                out.append(section.split(index__))
            elif this.type is None and (None is not before.type != after.type is not None):
                if index__ % width:
                    out.append(section.split(index__))
                else:
                    out.append(section.split(index__ + 1))
            return out + _split_core(section[1:], index__=index__)

        width = section.width.resolve()
        return _split_core(section, index__=0)


class MultiSection(_BaseSection, list[CompoundSection]):
    def __init__(self, base_index: int, src: T_MultiSection, env: _Environment):
        super().__init__(base_index, src, env)
        self.current_index = 0
        for section in src.sections:
            if isinstance(section, T_MultiSection):
                subsection = MultiSection(base_index + self.current_index, section, self)
                self += subsection
                self.current_index = subsection.current_index
            else:
                self.append(CompoundSection(base_index + self.current_index, section, self))
                self.current_index += 1


class Voice:
    def __init__(self, index: T_LevelIndex, src: T_Voice, env: _Environment):
        # --- setup env ---
        self.name = env.name.transform(index, src).resolve()
        self.time = env.time.transform(src.time, save=True)
        self.delay = env.delay.transform(None, save=True)
        self.beat = env.beat.transform(src.beat, save=True)
        self.trill_style = env.trill_style.transform(src.trill_style, save=True)
        self.position = env.position.anchor(index).transform(src.position, save=True)
        self.instrument = env.instrument.transform(src.instrument, save=True)
        self.dynamic = env.dynamic.transform(src.dynamic, save=True)
        self.sustain = env.sustain.transform(src.sustain, save=True)
        self.transpose = env.transpose.transform(src.transpose, save=True)
        # --- parse notes ---
        self.current_bar = 1  # bar indexing starts from 1
        self.current_pulse = 0  # but pulse starts from 0
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
            self.current_pulse = self_copy.current_pulse

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
        current_bar, current_pulse = self.current_bar, self.current_pulse

        def _resolve_core(note: T_SingleNote | T_SequentialNotes) -> Iterable[Iterable[Note]]:
            self.current_bar, self.current_pulse = current_bar, current_pulse
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
            self.current_pulse = 0
            self.current_bar = asserted_bar_number
        elif self.current_pulse != 0:
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
        current_bar, current_pulse = self.current_bar, self.current_pulse

        def transform(
            *noteblocks: NoteBlock | None,
            dynamic: Iterable[T_StaticAbsoluteDynamic],
            position: Iterable[T_PositionIndex],
        ):
            def apply_delay_and_position(noteblocks: Iterable[NoteBlock | None]) -> Iterable[Note]:
                for noteblock, note_position in zip(noteblocks, position, strict=False):
                    yield self._create_note(noteblock=noteblock, delay=delay, position=note_position)
                    if (pulse := self.current_pulse + 1) < time:
                        self.current_pulse = pulse
                    else:
                        self.current_pulse = 0
                        self.current_bar += 1

            def apply_dynamic(notes: Iterable[Note]) -> Iterable[Iterable[Note]]:
                return map(operator.mul, notes, dynamic)

            self.current_bar, self.current_pulse = current_bar, current_pulse
            return apply_dynamic(apply_delay_and_position(noteblocks))

        parallel_lines = multivalue_map(transform, *noteblocks, dynamic=dynamic, position=position)
        if type(parallel_lines) is T_MultiValue:
            merged_line = map(chain.from_iterable, transpose(parallel_lines))
            return deque(merged_line)
        return deque(parallel_lines)

    def _create_note(self, *, noteblock: NoteBlock | None, delay: T_Delay, position: T_PositionIndex):
        return Note(
            noteblock=noteblock,
            delay=delay,
            position=position,
            voice=self.name,
            where=(self.current_bar, self.current_pulse),
        )
