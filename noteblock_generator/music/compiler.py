from __future__ import annotations

from itertools import chain, repeat
from typing import Iterable

from .parser import (
    CompoundSection,
    DoubleDivisionNote,
    DoubleDivisionSection,
    MultiSection,
    Note,
    SingleDivisionNote,
    SingleDivisionSection,
)
from .properties import NoteBlock
from .typedefs import T_Delay, T_Tick, T_Width
from .utils import transpose


def compile(parsed_data: MultiSection) -> Music:  # noqa: A001
    return Music(parsed_data)  # TODO: error handling


class Unit(
    tuple[
        NoteBlock | None,
        NoteBlock | None,
        NoteBlock | None,
        NoteBlock | None,
    ]
):
    delay: T_Delay

    def __new__(cls, notes: Iterable[Note], *, delay: T_Delay):
        MAX_SLOT_COUNT = 4

        def collect_noteblocks(notes: Iterable[Note]) -> Iterable[NoteBlock | None]:
            skip_None = False
            for note in notes:
                if (noteblock := note.noteblock) is None:
                    if skip_None:
                        continue
                    skip_None = True
                yield noteblock

        noteblocks = tuple(collect_noteblocks(notes := tuple(notes)))
        if (L := len(noteblocks)) > MAX_SLOT_COUNT:
            raise ValueError(f"Slot overflow: {notes}")  # TODO: error handling
        padding = repeat(None, MAX_SLOT_COUNT - L)
        self = super().__new__(cls, chain(noteblocks, padding))
        self.delay = delay
        return self  # TODO: optimization: not every unit needs to be rendered

    def __bool__(self):
        return bool(filter(None, self))


class SingleDivision(list[list[Unit]]):
    width: T_Width
    tick: T_Tick

    def __init__(self, sequential_notes: SingleDivisionSection, max_level: int):
        def assign_levels(parallel_notes: list[SingleDivisionNote]) -> Iterable[Unit]:
            # parser guarantees that:
            #    - all parallel notes have at least one element
            #    - all parallel notes' delays are equal
            delay = parallel_notes[0].delay
            return (
                Unit(filter(lambda note: note.position == level, parallel_notes), delay=delay)
                for level in range(max_level + 1)
            )

        self.width = sequential_notes.width.resolve()
        self.tick = sequential_notes.tick.resolve()
        self += [list(e) for e in transpose(map(assign_levels, sequential_notes))]


class DoubleDivision(
    tuple[
        list[list[Unit]],
        list[list[Unit]],
    ]
):
    width: T_Width
    tick: T_Tick

    def __new__(cls, sequential_notes: DoubleDivisionSection, max_level: int):
        def assign_levels_left(parallel_notes: list[DoubleDivisionNote]) -> Iterable[Unit]:
            delay = parallel_notes[0].delay
            return (
                Unit(
                    # pyright bug
                    filter(lambda note: note.position[0] == 0 and note.position[1] == level, parallel_notes),  # pyright: ignore[reportGeneralTypeIssues]
                    delay=delay,
                )
                for level in range(max_level + 1)
            )

        def assign_levels_right(parallel_notes: list[DoubleDivisionNote]) -> Iterable[Unit]:
            delay = parallel_notes[0].delay
            return (
                Unit(
                    # pyright bug
                    filter(lambda note: note.position[0] == 1 and note.position[1] == level, parallel_notes),  # pyright: ignore[reportGeneralTypeIssues]
                    delay=delay,
                )
                for level in range(max_level + 1)
            )

        left_division = [list(e) for e in transpose(map(assign_levels_left, sequential_notes))]
        right_division = [list(e) for e in transpose(map(assign_levels_right, sequential_notes))]
        self = super().__new__(cls, (left_division, right_division))
        self.width = sequential_notes.width.resolve()
        self.tick = sequential_notes.tick.resolve()
        return self


class Section(list[SingleDivision | DoubleDivision]):
    def __init__(self, src: CompoundSection, nax_level: int):
        # TODO: initial padding
        for subsection in src:
            if isinstance(subsection, SingleDivisionSection):
                self.append(SingleDivision(subsection, nax_level))
            else:
                self.append(DoubleDivision(subsection, nax_level))


class Music(list[Section]):
    def __init__(self, src: MultiSection):
        max_level = src.max_level
        for section in src:
            self.append(Section(section, max_level))
