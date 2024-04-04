from __future__ import annotations

from typing import Iterable

from .parser import (
    CompoundSection,
    DoubleDivisionNote,
    DoubleDivisionSection,
    Dynamic,
    MultiSection,
    Note,
    NoteBlock,
    SingleDivisionNote,
    SingleDivisionSection,
)
from .typedefs import T_Delay, T_Tick, T_Tuple, T_Width
from .utils import transpose


def compile(parsed_data: MultiSection) -> Music:  # noqa: A001
    return Music(parsed_data)  # TODO: error handling


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
    width: T_Width
    tick: T_Tick

    def __init__(self, sequential_notes: SingleDivisionSection, *, min_level: int, max_level: int):
        def assign_levels(parallel_notes: list[SingleDivisionNote]) -> Iterable[Unit]:
            # parser guarantees that:
            #    - all parallel notes have at least one element
            #    - all parallel notes' delays are equal
            delay = parallel_notes[0].delay
            return (
                Unit(filter(lambda note: note.position == level, parallel_notes), delay=delay)
                for level in range(min_level, max_level + 1)
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

    def __new__(cls, sequential_notes: DoubleDivisionSection, *, min_level: int, max_level: int):
        def assign_levels_left(parallel_notes: list[DoubleDivisionNote]) -> Iterable[Unit]:
            # see comment in SingleDivision counterpart
            delay = parallel_notes[0].delay
            return (
                Unit(
                    # pyright bug
                    filter(lambda note: note.position[0] == 0 and note.position[1] == level, parallel_notes),  # type: ignore  # noqa: PGH003
                    delay=delay,
                )
                for level in range(min_level, max_level + 1)
            )

        def assign_levels_right(parallel_notes: list[DoubleDivisionNote]) -> Iterable[Unit]:
            delay = parallel_notes[0].delay
            return (
                Unit(
                    # pyright bug
                    filter(lambda note: note.position[0] == 1 and note.position[1] == level, parallel_notes),  # type: ignore  # noqa: PGH003
                    delay=delay,
                )
                for level in range(min_level, max_level + 1)
            )

        left_division = [list(e) for e in transpose(map(assign_levels_left, sequential_notes))]
        right_division = [list(e) for e in transpose(map(assign_levels_right, sequential_notes))]
        self = super().__new__(cls, (left_division, right_division))
        self.width = sequential_notes.width.resolve()
        self.tick = sequential_notes.tick.resolve()
        return self


class Section(list[SingleDivision | DoubleDivision]):
    def __init__(self, src: CompoundSection, *, min_level: int, max_level: int):
        # TODO: initial padding
        for subsection in src:
            if isinstance(subsection, SingleDivisionSection):
                self.append(SingleDivision(subsection, min_level=min_level, max_level=max_level))
            else:
                self.append(DoubleDivision(subsection, min_level=min_level, max_level=max_level))


class Music(list[Section]):
    def __init__(self, src: MultiSection):
        for section in src:
            self.append(Section(section, min_level=src.min_level, max_level=src.max_level))
