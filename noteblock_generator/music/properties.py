from __future__ import annotations

import contextlib
import re
from copy import copy as shallowcopy
from dataclasses import dataclass
from functools import partial, reduce
from itertools import chain
from pathlib import Path
from typing import ClassVar, Generic, Protocol, TypeVar, cast, final

from .typedefs import (
    T_AbsoluteDynamic,
    T_AbsoluteLevel,
    T_AbsoluteSustain,
    T_AbsoluteTranspose,
    T_Array,
    T_Beat,
    T_CompoundPosition,
    T_ConstantDynamic,
    T_Delete,
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
    T_Position,
    T_Positional,
    T_RelativeLevel,
    T_Reset,
    T_SingleDivisionPosition,
    T_Time,
    T_VariableDynamic,
    T_Width,
)
from .utils import (
    is_typeform,
    mutivalue_flatten,
    parse_duration,
    parse_timedvalue,
    positional_map,
    strip_split,
    typed_cache,
)

S, T, U, V = TypeVar("S"), TypeVar("T"), TypeVar("U"), TypeVar("V")


class SupportsName(Protocol):
    name: T_Name | None
    path: Path | None


class Name:
    def _init_core(self, index: T_Index = 0, src: SupportsName = None):
        if src is None:
            return ""
        if (name := src.name) is not None:
            return name
        if (path := src.path) is not None:
            return str(path.with_suffix(""))
        return f"Unnamed {type(src).__name__} {index}"

    def __init__(self):
        self._value = self._init_core()

    def transform(self, index: T_Index, src: SupportsName) -> Name:
        self = shallowcopy(self)
        if (name := src.name) is None:
            name = self._init_core(index, src)
        if self._value:
            self._value += "/"
        self._value += name
        return self

    def resolve(self) -> T_Name:
        return self._value


class Width:
    def __init__(self, value: T_Width = None):
        self._value = value

    def transform(self, time: T_Time, value: T_Width | None):
        if value is not None:
            return Width(value)
        elif self._value is None:
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
        self._value = self._original_value = value

    def transform(self, modifier: None | T_Reset | T, *, save=False):
        self = shallowcopy(self)
        if modifier is not None:
            if modifier == "$reset":
                self._value = self._original_value
            else:
                self._value = modifier
        if save:
            self._original_value = self._value
        return self

    def resolve(self) -> T:
        return self._value


class PositionalProperty(
    Generic[
        S,  # `__init__` argument type
        T,  # `transform` argument type
        U,  # internal representation type
        V,  # `resolve` output type
    ]
):
    @classmethod
    def _init_core(cls, value: S) -> U:
        return cast(U, value)

    @classmethod
    def _transform_core(cls, current: U, modifier: T) -> U:
        return cls._init_core(cast(S, modifier))

    @classmethod
    def _resolve_core(cls, current: U, *args, **kwargs) -> V:
        return cast(V, current)

    @final
    def __init__(self, value: T_Positional[S]):
        self._value = self._original_value = positional_map(self._init_core, value)

    @final
    @classmethod
    def _transform_core_wrapper(cls, origin: U, current: U, modifier: None | T_Reset | T_Delete | T) -> U | None:
        if modifier is None:
            return current
        if modifier == "$reset":
            return origin
        if modifier == "$del":
            return None
        return cls._transform_core(origin, modifier)

    @final
    def transform(self, modifier: T_Positional[T | T_Reset | T_Delete | None], *, save=False):
        self = shallowcopy(self)

        new_value = positional_map(self._transform_core_wrapper, self._original_value, self._value, modifier)
        if isinstance(new_value, T_MultiValue):
            new_value = T_MultiValue(filter(None, new_value))
            if new_value:
                self._value = new_value
            else:
                self._value = self._original_value
        elif new_value is None:
            self._value = self._original_value
        else:
            self._value = new_value
        if save:
            self._original_value = self._value
        return self

    @final
    def resolve(self, *args, **kwargs) -> T_Positional[V]:
        return positional_map(self._resolve_core, self._value, *args, **kwargs)


class SingleDivisionPosition(
    PositionalProperty[
        T_LevelIndex,
        T_SingleDivisionPosition,
        T_LevelIndex,
        T_LevelIndex,
    ]
):
    @classmethod
    def _transform_core(cls, current, modifier):
        if is_typeform(modifier, T_AbsoluteLevel):
            return modifier
        assert is_typeform(modifier, T_RelativeLevel), modifier
        return current + int(modifier)


class DoubleDivisionPosition(
    PositionalProperty[
        T_Index,
        T_Position,
        T_Index,
        T_DoubleIndex,
    ]
):
    @classmethod
    def _split_division_and_level(cls, value: T_CompoundPosition) -> tuple[T_Division, T_Level]:
        match = re.search("left|right|switch", value)
        assert match is not None, match  # match is guaranteed by T_CompoundPosition type
        division = cast(T_Division, match.group())
        level = value[match.end() :].strip()
        return division, level

    @classmethod
    def _transform_division(cls, current: T_DivisionIndex | None, modifier: T_Division | None):
        if modifier is None:
            return current
        if modifier == "switch":
            if current is None:
                return None
            return (current + 1) % 2
        if modifier == "bothsides":
            return None
        return cast(T_DivisionIndex, ["left", "right"].index(modifier))

    @classmethod
    def _transform_level(cls, current: T_LevelIndex, modifier: T_Level | None):
        if modifier is None:
            return current
        if is_typeform(modifier, T_AbsoluteLevel):
            return modifier
        return current + int(modifier)

    @classmethod
    @typed_cache
    def _transform_core(cls, current, modifier):
        if isinstance(current, T_LevelIndex):
            origin_division, origin_level = None, current
        else:
            origin_division, origin_level = current
        # ---
        if is_typeform(modifier, T_Level):
            transformation_division, transformation_level = None, modifier
        elif is_typeform(modifier, T_Division):
            transformation_division, transformation_level = cast(T_Division, modifier), None
        else:
            assert is_typeform(modifier, T_CompoundPosition), modifier
            transformation_division, transformation_level = cls._split_division_and_level(modifier)
        # ---
        division = cls._transform_division(origin_division, transformation_division)
        level = cls._transform_level(origin_level, transformation_level)
        if division is None:
            return level
        return division, level

    def resolve(self):  # type: ignore @final # TODO: refactor
        def handle_bothsides(current: T_Index) -> T_Positional[T_DoubleIndex]:
            if isinstance(current, T_LevelIndex):
                return T_MultiValue(((0, current), (1, current)))
            return current

        if isinstance(self._value, T_MultiValue):
            return mutivalue_flatten(map(handle_bothsides, self._value))
        return handle_bothsides(self._value)


@dataclass(kw_only=True, slots=True)
class NoteBlock:
    note: T_NoteValue
    instrument: str


class Instrument(
    PositionalProperty[
        T_Instrument,
        T_Instrument,
        T_Instrument,
        NoteBlock,
    ]
):
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

    @classmethod
    @typed_cache
    def _resolve_core(cls, current: T_Instrument, note_value: T_NoteValue):
        for instrument in strip_split(current, "/"):
            instrument_range = cls._INSTRUMENT_RANGE[instrument]  # guarantee valid key by T_Instrument
            with contextlib.suppress(ValueError):
                return NoteBlock(note=instrument_range.index(note_value), instrument=instrument)
        raise ValueError(f"Note out of range for {current}")  # TODO: error handling

    def get_octave(self):
        def get(value: T_Instrument):
            return (self._INSTRUMENT_RANGE[next(strip_split(value, "/"))].start - 6) // 12 + 2

        return positional_map(get, self._value)


class Dynamic(
    PositionalProperty[
        T_GlobalDynamic,
        T_LocalDynamic,
        T_Array[T_LocalDynamic],
        T_Array[T_AbsoluteDynamic],
    ]
):
    @classmethod
    def _init_core(cls, value):
        return (value,)

    @classmethod
    def _transform_core(cls, current, modifier):
        if is_typeform(modifier, T_GlobalDynamic):
            return cls._init_core(modifier)
        return (*current, modifier)

    @classmethod
    @typed_cache
    def _resolve_core(
        cls,
        current: T_Array[T_LocalDynamic],
        beat: T_Beat,
        sustain_duration: T_Duration,
        note_duration: T_Duration,
    ):
        def parse(value: T_LocalDynamic) -> list[T_ConstantDynamic]:
            if is_typeform(value, T_ConstantDynamic):
                return [value] * sustain_duration
            assert is_typeform(value, T_VariableDynamic), value

            def parse_variable_dynamic(tokens: list[T_VariableDynamic]) -> list[T_ConstantDynamic]:
                dynamic = tokens[0]
                if not dynamic.startswith(("+", "-")):
                    dynamic = int(dynamic)
                duration = parse_duration(*tokens[1:], beat=beat)
                if duration < 0:
                    duration += sustain_duration
                return [dynamic] * duration

            tokens = strip_split(value, ",")
            timed_values = map(parse_timedvalue, tokens)
            transformations = map(parse_variable_dynamic, timed_values)
            out = list(chain(*transformations))
            if (remaining_duration := sustain_duration - len(out)) < 0:
                raise ValueError("Incompatible sustain and duration")  # TODO: error handling
            return out + ["+0"] * remaining_duration

        def apply_transformation(current: T_AbsoluteDynamic, modifier: T_ConstantDynamic) -> T_AbsoluteDynamic:
            if isinstance(modifier, int):
                return modifier
            current += int(modifier)
            low_limit = min(1, current)
            high_limit = 4
            return min(max(current, low_limit), high_limit)

        transform = partial(reduce, apply_transformation)
        transformations = zip(*map(parse, current), strict=True)
        result = [int(e) for e in map(transform, transformations)]
        padding = [0] * (note_duration - sustain_duration)
        return T_Array(result + padding)


class Sustain(
    PositionalProperty[
        T_GlobalSustain,
        T_LocalSustain,
        T_Array[T_LocalSustain],
        T_AbsoluteSustain,
    ]
):
    @classmethod
    def _init_core(cls, value):
        return (value,)

    @classmethod
    def _transform_core(cls, current, modifier):
        if is_typeform(modifier, T_GlobalSustain):
            return cls._init_core(modifier)
        return (*current, modifier)

    @classmethod
    @typed_cache
    def _resolve_core(
        cls,
        current: T_Array[T_LocalSustain],
        beat: T_Beat,
        note_duration: T_Duration,
    ):
        out = 1
        for sustain in current:
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


class Transpose(
    PositionalProperty[
        T_GlobalTranspose,
        T_LocalTranspose,
        T_AbsoluteTranspose,
        T_AbsoluteTranspose,
    ]
):
    @classmethod
    def _transform_core(cls, current, modifier):
        if isinstance(modifier, T_GlobalTranspose):
            return int(modifier)
        return current + int(modifier)
