from __future__ import annotations

import contextlib
import re
from copy import copy as shallowcopy
from dataclasses import dataclass
from functools import partial, reduce
from itertools import chain
from pathlib import Path
from typing import ClassVar, Generic, Optional, Protocol, TypeVar, cast

from .typedefs import (
    T_AbsoluteDynamic,
    T_AbsoluteLevel,
    T_AbsoluteSustain,
    T_AbsoluteTranspose,
    T_Beat,
    T_CompoundPosition,
    T_ConstantDynamic,
    T_Default,
    T_Division,
    T_DivisionIndex,
    T_DoubleIndex,
    T_Duration,
    T_GlobalDynamic,
    T_GlobalSustain,
    T_GlobalTranspose,
    T_Index,
    T_Instrument,
    T_Level,
    T_LevelIndex,
    T_LocalDynamic,
    T_LocalSustain,
    T_LocalTranspose,
    T_MultiValue,
    T_Name,
    T_NoteValue,
    T_Optional,
    T_Position,
    T_Positional,
    T_RelativeLevel,
    T_SingleDivisionPosition,
    T_Time,
    T_TimedAbsoluteDynamic,
    T_TimedDynamic,
    T_TimedRelativeDynamic,
    T_Width,
)
from .utils import flatten, is_typeform, parse_duration, parse_timedvalue, positional_map, strip_split

S, T, U, V = TypeVar("S"), TypeVar("T"), TypeVar("U"), TypeVar("V")


class SupportsName(Protocol):
    name: T_Optional[T_Name]
    path: T_Optional[Path]


class Name:
    def _process(self, index: T_Index = 0, src: SupportsName = None):
        if src is None:
            return ""
        if not isinstance(name := src.name, T_Default):
            return name
        if not isinstance(path := src.path, T_Default):
            return str(path.with_suffix(""))
        return f"Unnamed {type(src).__name__} {index}"

    def __init__(self):
        self._value = self._process()

    def transform(self, index: T_Index, src: SupportsName) -> Name:
        self = shallowcopy(self)
        if isinstance(name := src.name, T_Default):
            name = self._process(index, src)
        if self._value:
            self._value += "/"
        self._value += name
        return self

    def resolve(self) -> T_Name:
        return self._value


class Width:
    def __init__(self, value: Optional[T_Width] = None):
        self._value = value

    def transform(self, time: T_Time, value: T_Optional[T_Width]):
        if not isinstance(value, T_Default):
            return Width(value)
        elif isinstance(self._value, T_Default):
            return Width(self._resolve_time(time))
        return self

    def _resolve_time(self, time: T_Time):
        for n in range(16, 7, -1):
            if not (time % n and n % time):
                return n

    def resolve(self) -> T_Width:
        return self._value or 12


class ImmutableProperty(Generic[T]):
    def __init__(self, value: T):
        self._value = value

    def transform(self, value: T_Optional[T]):
        if isinstance(value, T_Default):
            return self
        return type(self)(value)

    def resolve(self) -> T:
        return self._value


class PositionalProperty(Generic[S, T, U, V]):
    def _process(self, value: S) -> U:
        return cast(U, value)

    def _transform(self, origin: U, transformation: T) -> U:
        return self._process(cast(S, transformation))

    def _resolve(self, origin: U, *args, **kwargs) -> V:
        return cast(V, origin)

    def __init__(self, value: T_Positional[S]):
        self._value = positional_map(self._process, value)

    def transform(self, transformation: T_Positional[T_Optional[T]]):
        if isinstance(transformation, T_Default):
            return self
        self = shallowcopy(self)
        self._value = positional_map(self._transform, self._value, transformation)
        return self

    def resolve(self, *args, **kwargs) -> T_Positional[V]:
        return positional_map(self._resolve, self._value, *args, **kwargs)


class SingleDivisionPosition(PositionalProperty[T_LevelIndex, T_SingleDivisionPosition, T_LevelIndex, T_LevelIndex]):
    def _transform(self, origin, transformation):
        if is_typeform(transformation, T_AbsoluteLevel):
            return transformation
        assert is_typeform(transformation, T_RelativeLevel)
        return origin + int(transformation)


class DoubleDivisionPosition(PositionalProperty[T_Index, T_Position, T_Index, T_DoubleIndex]):
    def _split_division_and_level(self, value: T_CompoundPosition) -> tuple[T_Division, T_Level]:
        match = re.search("left|right|switch", value)
        assert match is not None  # match is guaranteed by T_CompoundPosition type
        division: T_Division = match.group()  # type: ignore
        level = value[match.end() :].strip()
        return division, level

    def _transform_division(
        self, origin: Optional[T_DivisionIndex], transformation: Optional[T_Division]
    ) -> Optional[T_DivisionIndex]:
        if transformation is None:
            return origin
        if transformation == "switch":
            if origin is None:
                return None
            return (origin + 1) % 2
        return ["left", "right"].index(transformation)  # type: ignore

    def _transform_level(self, origin: T_LevelIndex, transformation: Optional[T_Level]):
        if transformation is None:
            return origin
        if is_typeform(transformation, T_AbsoluteLevel):
            return transformation
        return origin + int(transformation)

    def _transform(self, origin, transformation):
        if isinstance(origin, T_LevelIndex):
            origin_division, origin_level = None, origin
        else:
            origin_division, origin_level = origin
        # ---
        if is_typeform(transformation, T_Level):
            transformation_division, transformation_level = None, transformation
        elif is_typeform(transformation, T_Division):
            transformation_division, transformation_level = transformation, None
        else:
            assert is_typeform(transformation, T_CompoundPosition)
            transformation_division, transformation_level = self._split_division_and_level(transformation)
        # ---
        division = self._transform_division(origin_division, transformation_division)  # type: ignore
        level = self._transform_level(origin_level, transformation_level)
        if division is None:
            return level
        return division, level

    def transform(self, transformation):
        if isinstance(transformation, T_Default):
            return super().transform(transformation)

        def handle_bothsides(transformation: T_Optional[T_Position]) -> T_Positional[T_Optional[T_Position]]:
            if is_typeform(transformation, T_Default | T_Level):
                return transformation
            if is_typeform(transformation, T_Division):
                if transformation == "bothsides":
                    return T_MultiValue(("left", "right"))
                return transformation
            assert is_typeform(transformation, T_CompoundPosition)
            division, level = self._split_division_and_level(transformation)
            if division == "bothsides":
                return T_MultiValue((f"left{level}", f"right{level}"))
            return transformation

        if isinstance(transformation, T_MultiValue):
            return super().transform(flatten(map(handle_bothsides, transformation)))
        return super().transform(handle_bothsides(transformation))

    def resolve(self):
        def handle_bothsides(origin: T_Index) -> T_Positional[T_DoubleIndex]:
            if isinstance(origin, T_LevelIndex):
                return T_MultiValue(((0, origin), (1, origin)))
            return origin

        if isinstance(self._value, T_MultiValue):
            return flatten(map(handle_bothsides, self._value))
        return handle_bothsides(self._value)


@dataclass(kw_only=True, slots=True)
class NoteBlock:
    note: T_NoteValue
    instrument: str


class Instrument(PositionalProperty[T_Instrument, T_Instrument, T_Instrument, NoteBlock]):
    _INSTRUMENT_RANGE: ClassVar = {
        "basedrum": range(6, 31),
        "hat": range(6, 31),
        "snare": range(6, 31),
        "bass": range(6, 31),
        "didgeridoo": range(6, 31),
        "guitar": range(18, 43),
        "banjo": range(30, 55),
        "bit": range(30, 55),
        "harp": range(30, 55),
        "iron_xylophone": range(30, 55),
        "pling": range(30, 55),
        "cow_bell": range(42, 67),
        "flute": range(42, 67),
        "bell": range(54, 79),
        "xylophone": range(54, 79),
        "chime": range(54, 79),
    }

    def _resolve(self, origin: T_Instrument, note_value: T_NoteValue):
        for instrument in strip_split(origin, "/"):
            instrument_range = self._INSTRUMENT_RANGE[instrument]  # guarantee valid key by T_Instrument
            with contextlib.suppress(ValueError):
                return NoteBlock(note=instrument_range.index(note_value), instrument=instrument)
        raise ValueError(f"Note out of range for {origin}")  # TODO: error handling

    def get_octave(self):
        def get(origin: T_Instrument):
            return (self._INSTRUMENT_RANGE[next(strip_split(origin, "/"))].start - 6) // 12 + 2

        return positional_map(get, self._value)


class Dynamic(PositionalProperty[T_GlobalDynamic, T_LocalDynamic, list[T_LocalDynamic], list[T_AbsoluteDynamic]]):
    def _process(self, value):
        return [value]

    def _transform(self, origin, transformation):
        if is_typeform(transformation, T_GlobalDynamic):
            return self._process(transformation)
        return [*origin, transformation]

    def _resolve(self, origin: list[T_LocalDynamic], beat: T_Beat, sus_duration: T_Duration, note_duration: T_Duration):
        def parse(value: T_LocalDynamic) -> list[T_ConstantDynamic]:
            if is_typeform(value, T_ConstantDynamic):
                return [value] * sus_duration

            assert is_typeform(value, T_TimedAbsoluteDynamic | T_TimedRelativeDynamic)

            def parse_timed_dynamic(tokens: list[T_TimedDynamic]) -> list[T_ConstantDynamic]:
                dynamic = tokens[0]
                if not dynamic.startswith(("+", "-")):
                    dynamic = int(dynamic)
                duration = parse_duration(*tokens[1:], beat=beat)
                if duration < 0:
                    duration += sus_duration
                return [dynamic] * duration

            tokens = strip_split(value, ",")
            timed_dynamics = map(parse_timedvalue, tokens)
            transformations = map(parse_timed_dynamic, timed_dynamics)
            out = list(chain(*transformations))
            if (remaining_duration := sus_duration - len(out)) < 0:
                raise ValueError("Incompatible sustain and duration")  # TODO: error handling
            return out + ["+0"] * remaining_duration

        def apply_transformation(origin: T_AbsoluteDynamic, transformation: T_ConstantDynamic) -> T_AbsoluteDynamic:
            if isinstance(transformation, int):
                return transformation
            origin += int(transformation)
            low_limit = min(1, origin)
            high_limit = 4
            return min(max(origin, low_limit), high_limit)

        transform = partial(reduce, apply_transformation)
        transformations = zip(*map(parse, origin), strict=True)
        result = map(int, map(transform, transformations))
        padding = [0] * (note_duration - sus_duration)
        return list(result) + padding


class Sustain(PositionalProperty[T_GlobalSustain, T_LocalSustain, list[T_LocalSustain], T_AbsoluteSustain]):
    def _process(self, value):
        return [value]

    def _transform(self, origin, transformation):
        if is_typeform(transformation, T_GlobalSustain):
            return self._process(transformation)
        return [*origin, transformation]

    def _resolve(self, origin: list[T_LocalSustain], beat: T_Beat, note_duration: T_Duration):
        out = 1
        for sustain in origin:
            relative = False
            if isinstance(sustain, bool):
                duration = note_duration if sustain else 1
            elif isinstance(sustain, int):
                duration = sustain if sustain > 0 else note_duration + sustain
            else:
                duration = parse_duration(sustain, beat=beat)
                relative = sustain.startswith(("+", "-"))
            if relative:
                out += duration
            else:
                out = duration if duration > 0 else note_duration + duration

        low_limit, high_limit = 1, note_duration
        return min(max(out, low_limit), high_limit)


class Transpose(PositionalProperty[T_GlobalTranspose, T_LocalTranspose, T_AbsoluteTranspose, T_AbsoluteTranspose]):
    def _transform(self, origin, transformation):
        if isinstance(transformation, T_GlobalTranspose):
            return int(transformation)
        return origin + int(transformation)
