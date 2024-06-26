from __future__ import annotations

from contextlib import contextmanager
from enum import Enum
from itertools import chain, pairwise
from typing import Iterable, Literal

from .parser import Chord, Composition, Movement, Note, NoteBlock, Section
from .properties import Dynamic, T_LevelIndex
from .utils import transpose
from .validator import T_Delay, T_Tick, T_Tuple, T_Width


def compile(parsed_data: Composition) -> T_Data:  # noqa: A001
    return _Compiler(parsed_data).generate()


class Unit(T_Tuple[NoteBlock]):  # TODO: optimization: not every unit needs to be generated
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
        return self

    def __bool__(self):
        return bool(filter(None, self))


class SingleDivision(list[list[Unit]]):
    @classmethod
    def from_src(cls, sequential_notes: Section, *, min_level: T_LevelIndex, max_level: T_LevelIndex):
        def assign_levels(chord: Chord) -> Iterable[Unit]:
            return (
                Unit(filter(lambda note: note.level == level, chord), delay=chord.delay)
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
    def from_src(cls, section: Section, *, min_level: T_LevelIndex, max_level: T_LevelIndex):
        def create_subdivision(division: Literal[0, 1]):
            def assign_levels(chord: Chord) -> Iterable[Unit]:
                return (
                    Unit(
                        filter(lambda note: note.division == division and note.level == level, chord),
                        delay=chord.delay,
                    )
                    for level in range(min_level, max_level + 1)
                )

            return SingleDivision(
                transpose(map(assign_levels, section)),
                width=width,
                tick=tick,
            )

        width = section.width.resolve()
        tick = section.tick.resolve()
        return cls(map(create_subdivision, (0, 1)))

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


_Section = SingleDivision | DoubleDivision


class _Movement(list[_Section]):
    def __init__(self, src: Movement, *, min_level: T_LevelIndex, max_level: T_LevelIndex):
        # TODO: initial padding
        for section in src:
            if section.type == "single":
                self.append(SingleDivision.from_src(section, min_level=min_level, max_level=max_level))
            else:
                self.append(DoubleDivision.from_src(section, min_level=min_level, max_level=max_level))

        self.length = sum(section.length for section in self)
        self.height = self[0].height


class _Composition(list[_Movement]):
    def __init__(self, src: Composition):
        levels = tuple(chain.from_iterable(section.level_iter() for movement in src for section in movement))
        if levels:
            min_level, max_level = min(levels), max(levels)
        else:
            min_level = max_level = 0

        for movement in src:
            self.append(_Movement(movement, min_level=min_level, max_level=max_level))

        self.length = sum(movement.length for movement in self)
        self.height = self[0].height


class Direction(tuple[int, int], Enum):
    # coordinates in (x, z)
    north = (0, -1)
    south = (0, 1)
    east = (1, 0)
    west = (-1, 0)

    def __str__(self):
        return self.name

    def __mul__(self, other: tuple[int, int]) -> tuple[int, int]:
        """Complex multiplication, with (x, z) representing x + zi"""
        return (
            self[0] * other[0] - self[1] * other[1],
            self[0] * other[1] + self[1] * other[0],
        )

    def __neg__(self):
        return Direction(self * Direction((-1, 0)))


class Block:
    Clear: Literal[0] = 0
    Generic: Literal[1] = 1

    def __init__(self, name: str, **properties):
        self.name = name
        self.properties = properties

    @classmethod
    def NoteBlock(cls, noteblock: NoteBlock | None):
        if noteblock is None:
            return cls.Clear
        return cls("note_block", note=noteblock.note, instrument=noteblock.instrument)

    @classmethod
    def Repeater(cls, *, delay: T_Delay, direction: Direction):
        direction = -direction  # MINECRAFT's BUG: repeater's direction is reversed
        return cls("repeater", delay=delay, facing=direction)

    @classmethod
    def Redstone(cls, *connections: Direction):
        # Connected to all sides by default
        if not connections:
            connections = tuple(Direction)
        # Only allow connecting sideways, because that's all we need for this build
        return cls("redstone_wire", **{Direction(i).name: "side" for i in connections})

    def __eq__(self, other: object):
        return isinstance(other, Block) and self.name == other.name and self.properties == other.properties


T_Coordinates = tuple[int, int, int]
T_Block = Block | Literal[0, 1]
T_Data = dict[T_Coordinates, T_Block]


class _Compiler:
    # TODO: handle multiple widths
    # TODO: implement tick

    def __init__(self, src: Composition):
        self.X, self.Y, self.Z = (0, 0, 0)
        self.x_dir, self.z_dir = Direction((1, 0)), Direction((0, 1))
        self._data: T_Data = {}
        self._composition = _Composition(src)

    @property
    def z_i(self) -> Literal[1, -1]:
        return self.z_dir[1]  # pyright: ignore[reportGeneralTypeIssues]

    @z_i.setter
    def z_i(self, value: Literal[1, -1]):
        self.z_dir = Direction((0, value))

    @contextmanager
    def localize(self, x=0, y=0, z=0):
        original_x, original_y, original_z = self.X, self.Y, self.Z
        self.X += x
        self.Y += y
        self.Z += self.z_i * z

        try:
            yield self
        finally:
            self.X, self.Y, self.Z = original_x, original_y, original_z

    def __setitem__(self, coordinates: T_Coordinates, value: T_Block):
        with self.localize(*coordinates) as self:
            if (self.X, self.Y, self.Z) in self._data and value == Block.Clear:
                return
            self._data[self.X, self.Y, self.Z] = value

    def generate(self):
        x = self.X
        for movement in self._composition:
            with self.localize() as self:
                self.generate_movement(movement)
                x = self.X
            self.X = x + 4
        return self._data

    def generate_movement(self, movement: _Movement):
        self.generate_section(movement[0])
        for this_section, next_section in pairwise(movement):
            self.generate_bridge(this_section, next_section)
            self.generate_section(next_section)

    def generate_section(self, section: _Section):
        if isinstance(section, SingleDivision):
            self._single_division(section)
        else:
            self._double_division(section)

    def _single_division(self, section: SingleDivision):
        x, z = self.X, self.Z
        for i, level in enumerate(section):
            with self.localize(y=2 * i) as self:
                self.generate_level(level, width=section.width)
                x, z = self.X, self.Z
        self.X, self.Z = x, z

    def _double_division(self, section: DoubleDivision):
        x, z = self.X, self.Z
        left_division, right_division = section
        with self.localize() as self:
            self.generate_section(left_division)
            x, z = self.X, self.Z
        with self.localize(z=2 * section.width + 4) as self:
            self.generate_section(right_division)
        self.X, self.Z = x, z

    def generate_bridge(self, from_section: _Section, to_section: _Section):
        if isinstance(from_section, SingleDivision):
            if isinstance(to_section, SingleDivision):
                self._single_to_single(from_section, to_section)
            else:
                self._single_to_double(from_section, to_section)
        else:  # noqa: PLR5501
            if isinstance(to_section, SingleDivision):
                self._double_to_single(from_section, to_section)
            else:
                self._double_to_double(from_section, to_section)

    def _single_to_single(self, from_section: SingleDivision, to_section: SingleDivision):
        x, z = self.X, self.Z
        for i, row in enumerate(from_section):
            with self.localize(y=2 * i) as self:
                self.generate_rows_bridge(delay=row[-1].delay)
                x, z = self.X, self.Z
        self.X, self.Z = x, z

    def _double_to_double(self, from_section: DoubleDivision, to_section: DoubleDivision):
        from_L, from_R = from_section
        to_L, to_R = to_section

        x, z = self.X, self.Z
        with self.localize() as self:
            self.generate_bridge(from_L, to_L)
            x, z = self.X, self.Z
        with self.localize(z=2 * from_section.width + 4) as self:
            self.generate_bridge(from_R, to_R)
        self.X, self.Z = x, z

    def _single_to_double(self, from_section: SingleDivision, to_section: DoubleDivision): ...  # TODO

    def _double_to_single(self, from_section: DoubleDivision, to_section: SingleDivision): ...  # TODO

    def generate_level(self, level: list[Unit], *, width: T_Width):
        for i, (unit, _) in enumerate(pairwise(level)):
            self.generate_unit(unit, mode="normal" if (i + 1) % width else "end_of_row")
        self.generate_unit(level[-1], mode="end_of_section")

    NOTEBLOCK_PLACEMENTS = (-1, 0), (-1, 1), (1, 0), (1, 1), (-2, 0), (2, 0)
    ROW_BRIDGE = (0, 1), (0, 2), (1, 2), (2, 2), (2, 1), (3, 1), (4, 1), (4, 0)

    def generate_unit(self, unit: Unit, *, mode: Literal["normal", "end_of_row", "end_of_section"]):
        self[0, -1, 0] = Block.Generic
        self[0, 1, 0] = Block.Generic
        self[0, 1, 1] = Block.Generic
        self[0, 0, 0] = Block.Redstone()

        unit_iter = iter(unit)
        for x, z in self.NOTEBLOCK_PLACEMENTS:
            self[x, 0, z] = Block.NoteBlock(next(unit_iter, None))

        if mode == "normal":
            self[0, 1, 1] = Block.Repeater(delay=unit.delay, direction=self.z_dir)
            self.Z += self.z_i * 2
        elif mode == "end_of_row":
            self.generate_rows_bridge(delay=unit.delay)

    def generate_rows_bridge(self, *, delay: T_Delay):
        with Circuit(self) as circuit:
            for x, z in self.ROW_BRIDGE[:-1]:
                circuit[x, 1, z] = "wire"
            x, z = self.ROW_BRIDGE[-1]
            circuit[x, 1, z] = delay

        self.z_i *= -1
        self.X += x
        self.Z += self.z_i * (z + 1)


class Circuit(dict[T_Coordinates, Literal["wire"] | T_Delay]):
    # The series of redstones is assumed to form a valid circuit, there are no runtime checks.

    def __init__(self, compiler: _Compiler):
        self._compiler = compiler

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self:
            self._clear_space()
            self._generate_base()
            self._generate_redstones()

    def _clear_space(self):
        for x, y, z in self:
            self._compiler[x + 1, y, z] = Block.Clear
            self._compiler[x - 1, y, z] = Block.Clear
            self._compiler[x, y + 1, z] = Block.Clear
            self._compiler[x, y, z + 1] = Block.Clear
            self._compiler[x, y, z - 1] = Block.Clear

    def _generate_base(self):
        coordinates = tuple(self)
        self._compiler[coordinates[0]] = Block.Generic
        for (this_x, this_y, this_z), (next_x, next_y, next_z) in pairwise(coordinates):
            if this_y > next_y:
                self._compiler[next_x, next_y - 1, next_z] = Block("glass")
            elif this_y < next_y:
                self._compiler[this_x, this_y - 1, this_z] = Block("glass")
                self._compiler[next_x, next_y - 1, next_z] = Block.Generic
            else:
                self._compiler[next_x, next_y - 1, next_z] = Block.Generic

    def _generate_redstones(self):
        if len(self) >= 3:
            self.__generate_redstones_case_3()
        elif len(self) == 2:
            self.__generate_redstones_case_2()
        else:
            self.__generate_redstones_case_1()

    def __generate_redstones_case_1(self):
        coordinates, value = next(iter(self.items()))
        if value == "wire":
            self._compiler[coordinates] = Block.Redstone()
        else:
            self._compiler[coordinates] = Block.Repeater(delay=value, direction=self._compiler.z_dir)

    def __generate_redstones_case_2(self):
        coordinates_1, coordinates_2 = self.keys()
        direction = Direction((coordinates_2[0] - coordinates_1[0], coordinates_2[2] - coordinates_1[2]))
        for coordinates, value in self.items():
            if value == "wire":
                self._compiler[coordinates] = Block.Redstone(direction)
            else:
                self._compiler[coordinates] = Block.Repeater(delay=value, direction=direction)

    def __generate_redstones_case_3(self):
        circuit = tuple(self.items())

        for i in range(len(circuit) - 2):
            (coordinates_1, value_1), (coordinates_2, value_2), (coordinates_3, value_3) = circuit[i : i + 3]
            direction_12 = Direction((coordinates_2[0] - coordinates_1[0], coordinates_2[2] - coordinates_1[2]))
            direction_23 = Direction((coordinates_3[0] - coordinates_2[0], coordinates_3[2] - coordinates_2[2]))

            if i == 0:
                if value_1 == "wire":
                    self._compiler[coordinates_1] = Block.Redstone(direction_12)
                else:
                    self._compiler[coordinates_1] = Block.Repeater(delay=value_1, direction=direction_12)
                continue

            if value_2 == "wire":
                self._compiler[coordinates_2] = Block.Redstone(-direction_12, direction_23)
            else:
                self._compiler[coordinates_2] = Block.Repeater(delay=value_2, direction=direction_23)

            if i + 3 == len(circuit):
                if value_3 == "wire":
                    self._compiler[coordinates_3] = Block.Redstone(direction_23)
                else:
                    self._compiler[coordinates_3] = Block.Repeater(delay=value_3, direction=direction_23)
