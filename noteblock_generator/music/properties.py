from __future__ import annotations

import functools
import math
import re
from collections import deque
from copy import copy as shallowcopy
from dataclasses import dataclass
from itertools import chain, islice, repeat
from pathlib import Path
from typing import TYPE_CHECKING, Generic, Hashable, Iterable, Literal, Protocol, TypeVar, cast

from .data import INSTRUMENT_RANGE, NOTE_VALUE
from .typedefs import (
    T_AbsoluteDynamic,
    T_AbsoluteSustain,
    T_Beat,
    T_CompoundPosition,
    T_Delay,
    T_Delete,
    T_Division,
    T_Duration,
    T_Dynamic,
    T_Instrument,
    T_MultiValue,
    T_Name,
    T_NoteValue,
    T_Position,
    T_Positional,
    T_PositionalProperty,
    T_Reset,
    T_StaticAbsoluteDynamic,
    T_StaticAbsoluteLevel,
    T_StaticAbsolutePosition,
    T_StaticCompoundPosition,
    T_StaticDynamic,
    T_StaticLevel,
    T_StaticPosition,
    T_StaticProperty,
    T_StaticRelativeLevel,
    T_Sustain,
    T_Tick,
    T_Time,
    T_Transpose,
    T_TrillStyle,
    T_Tuple,
    T_VariableCompoundPosition,
    T_VariableDynamic,
    T_VariableLevel,
    T_Width,
    is_typeform,
)
from .utils import (
    multivalue_flatten,
    multivalue_map,
    parse_duration,
    split_timedvalue,
    strip_split,
    transpose,
    typed_cache,
)


class SupportsName(Protocol):
    name: T_Name | None
    path: Path | None


class Name:
    def _init_core(self, index: int | tuple[int, int] = 0, src: SupportsName = None):
        if src is None:
            return ""
        if (name := src.name) is not None:
            return name.replace(" ", "_")
        if (path := src.path) is not None:
            return path.stem
        return f"{type(src).__name__}-{index}"

    def __init__(self):
        self._value = self._init_core()

    def transform(self, index: int | tuple[int, int], src: SupportsName) -> Name:
        self = shallowcopy(self)
        name = self._init_core(index, src)
        self._value += f"/{name}"
        return self

    def resolve(self) -> T_Name:
        return self._value


class Width:
    def __init__(self, value: T_Width = None):
        self._value = value

    def transform(self, time: T_Time, value: T_Width | None):
        if value is not None:
            return Width(value)
        if self._value is None:
            return Width(self._resolve_time(time))
        return self

    def _resolve_time(self, time: T_Time):
        for n in range(16, 7, -1):
            if not (time % n and n % time):
                return n

    def resolve(self) -> T_Width:
        return self._value or 12


S = TypeVar("S")
T = TypeVar("T", bound=Hashable)
U = TypeVar("U", bound=Hashable)
V = TypeVar("V")


class _StaticProperty(Generic[T]):
    _DEFAULT: T

    def __init__(self):
        self._value = self._original_value = self._DEFAULT

    @typed_cache
    def transform(self, modifier: T_StaticProperty[T], *, save=False):
        self = shallowcopy(self)
        if modifier is not None:
            if modifier == "$reset":
                self._value = self._original_value
            else:
                self._value = cast(T, modifier)
        if save:
            self._original_value = self._value
        return self

    def resolve(self) -> T:
        return self._value


class Time(_StaticProperty[T_Time]):
    _DEFAULT = 16


class Delay(_StaticProperty[T_Delay]):
    _DEFAULT = 1


class Beat(_StaticProperty[T_Beat]):
    _DEFAULT = 2


class Tick(_StaticProperty[T_Tick]):
    _DEFAULT = 20.0


class TrillStyle(_StaticProperty[T_TrillStyle]):
    _DEFAULT = "normal"


def _is_empty(positional_value: T_Positional):
    return type(positional_value) is T_MultiValue and not positional_value


class _PositionalProperty(
    Generic[
        T,  # internal representation type
        U,  # `transform` argument type
        V,  # `resolve` output type
    ]
):
    _DEFAULT: T
    _NULL_VALUE: T_Positional[V] = T_MultiValue()
    _original_value: T_Positional[T]
    _value: T_Positional[T]

    def _transform_core(self, current: T, modifier: U) -> T:
        # must override if T != U
        return cast(T, modifier)

    def _resolve_core(self, current: T) -> V:
        # must override if T != V, or if resolve_core should take more arguments
        return cast(V, current)

    def __init__(self):
        self._value = self._original_value = self._DEFAULT

    def _transform_core_wrapper(self, origin: T, current: T, modifier: U | T_Reset | T_Delete | None) -> T | T_Delete:
        if modifier is None:
            return current
        if modifier == "$reset":
            return origin
        if modifier == "$del":
            return "$del"
        return self._transform_core(current, modifier)

    def _prepare_transform(self, modifier: T_PositionalProperty[U]) -> T_PositionalProperty[U]:
        if type(modifier) is not T_MultiValue:
            return modifier

        modifier_len = len(modifier)
        working_modifier = list(modifier)  # convert to list to allow mutation

        if type(self._value) is T_MultiValue:
            current_len = len(self._value)
            # fewer modifiers than current values -> implicit delete
            if modifier_len < current_len:
                working_modifier += ("$del" for _ in range(current_len - modifier_len))
            # more modifiers than current values -> apply extra modifiers to _DEFAULT
            elif modifier_len > current_len:
                self._value += (self._DEFAULT for _ in range(modifier_len - current_len))

        def replace(iterable: Iterable[S], old: S, new: S) -> Iterable[S]:
            for element in iterable:
                if element == old:
                    yield new
                else:
                    yield element

        if type(self._original_value) is T_MultiValue:
            original_len = len(self._original_value)
            # replace every "$reset" modifier with "$del" if it overflows original value
            if modifier_len > original_len:
                inbound_modifiers = working_modifier[:original_len]
                outbound_modifiers = replace(working_modifier[original_len:], "$reset", "$del")
                working_modifier = inbound_modifiers + list(outbound_modifiers)

        # no idea why pyright complains
        return T_MultiValue(working_modifier)  # pyright: ignore[reportGeneralTypeIssues]

    @typed_cache
    def transform(self, modifier: T_PositionalProperty[U], *, save=False):
        self = shallowcopy(self)
        modifier = self._prepare_transform(modifier)

        new_value = multivalue_map(self._transform_core_wrapper, self._original_value, self._value, modifier)
        if type(new_value) is T_MultiValue:
            self._value = T_MultiValue(e for e in new_value if e != "$del")
        elif new_value == "$del":
            self._value = T_MultiValue()
        else:
            self._value = new_value
        if save:
            self._original_value = self._value
        return self

    @typed_cache
    def resolve(self, *args, **kwargs) -> T_Positional[V]:
        if _is_empty(out := multivalue_map(self._resolve_core, self._value, *args, **kwargs)):
            return self._NULL_VALUE
        return out


T_LevelIndex = int
T_DivisionIndex = Literal[0, 1] | None  # None stands for no division, for single-division sections
T_PositionIndex = tuple[T_DivisionIndex, T_LevelIndex] | None  # None stands for no position, for rests

_T_SpecialDivisionIndex = T_DivisionIndex | Literal[True]  # True stands for bothsides
_T_SpecialPositionIndex = tuple[_T_SpecialDivisionIndex, T_LevelIndex] | None


class Position(
    _PositionalProperty[
        T_Tuple[T_Position],
        T_Position,
        Iterable[T_PositionIndex],
    ],
):
    _DEFAULT: T_Tuple[T_StaticAbsoluteLevel]
    _NULL_VALUE: Iterable[None] = repeat(None)

    def anchor(self, index: T_LevelIndex):
        def apply(previous_values: T_Tuple[T_Position]) -> T_Tuple[T_Position]:
            return (index, *previous_values)

        self = shallowcopy(self)
        self._original_value = self._DEFAULT = (index,)
        self._value = multivalue_map(apply, self._value)
        return self

    def _transform_core(self, current, modifier) -> T_Tuple[T_Position]:
        if is_typeform(modifier, T_StaticAbsolutePosition):
            return (modifier,)
        return (*current, modifier)

    def _resolve_core(
        self,
        current: T_Tuple[T_Position],
        beat: T_Beat,
        sustain_duration: T_Duration,
        note_duration: T_Duration,
    ) -> Iterable[_T_SpecialPositionIndex]:
        def parse_to_static(value: T_Position) -> Iterable[T_StaticPosition]:
            def split_variable_position(value: T_VariableCompoundPosition) -> tuple[T_Division, T_VariableLevel]:
                match = re.search(r"(M|L|R|LR|SW)", value)
                assert match is not None, match
                division = match.group()
                assert is_typeform(division, T_Division)
                level = value[match.end() :].strip()
                assert is_typeform(level, T_VariableLevel)
                return cast(T_Division, division), level

            def parse_variable_level(value: T_VariableLevel) -> Iterable[T_StaticLevel]:
                def core(timedvalue: list[T_VariableLevel]) -> Iterable[T_StaticLevel]:
                    level = timedvalue[0]
                    if not level.startswith(("+", "-")):
                        level = int(level)
                    duration = parse_duration(*timedvalue[1:], beat=beat)
                    if duration < 0:
                        duration += sustain_duration
                    return repeat(level, duration)

                tokens = strip_split(value, ",")
                timed_values = map(split_timedvalue, tokens)
                transformations = map(core, timed_values)
                result = chain.from_iterable(transformations)
                return islice(chain(result, repeat("+0")), sustain_duration)

            def merge_static_position(division: T_Division, level: T_StaticLevel) -> T_StaticPosition:
                return division + str(level)

            if is_typeform(value, T_StaticPosition):
                return repeat(value, sustain_duration)
            if is_typeform(value, T_VariableCompoundPosition):
                division, value = split_variable_position(value)
                static_levels = parse_variable_level(value)
                return (merge_static_position(division, level) for level in static_levels)
            assert is_typeform(value, T_VariableLevel), value
            return parse_variable_level(value)

        def binary_transform(
            current: tuple[_T_SpecialDivisionIndex, T_LevelIndex],
            modifier: T_StaticPosition,
        ) -> tuple[_T_SpecialDivisionIndex, T_LevelIndex]:
            def split_position(value: T_StaticCompoundPosition) -> tuple[T_Division, T_StaticLevel]:
                match = re.search("[+-]?\\d+", value)
                assert match is not None, match
                level = match.group()
                if level.startswith(("+", "-")):
                    assert is_typeform(level, T_StaticRelativeLevel)
                else:
                    level = int(level)
                division = value[: match.start()]
                assert is_typeform(division, T_Division)
                return cast(T_Division, division), level

            def transform_division(current: _T_SpecialDivisionIndex, modifier: T_Division | None):
                if modifier is None:  # no changes
                    return current
                if modifier == "SW":
                    if current in (0, 1):
                        return (current + 1) % 2
                    return current
                if modifier == "M":
                    return None
                if modifier == "LR":
                    return True
                return cast(Literal[0, 1], ["L", "R"].index(modifier))

            def transform_level(current: int, modifier: T_StaticLevel | None) -> T_LevelIndex:
                if modifier is None:
                    return current
                if is_typeform(modifier, T_StaticAbsoluteLevel):
                    return modifier
                assert is_typeform(modifier, T_StaticRelativeLevel), modifier
                return current + int(modifier)

            if isinstance(current, int):
                origin_division, origin_level = None, current
            else:
                origin_division, origin_level = current
            # ---------
            if is_typeform(modifier, T_StaticLevel):
                transformation_division, transformation_level = None, modifier
            elif is_typeform(modifier, T_Division):
                transformation_division, transformation_level = cast(T_Division, modifier), None
            else:
                assert is_typeform(modifier, T_CompoundPosition), modifier
                transformation_division, transformation_level = split_position(modifier)
            # ---------
            division = transform_division(origin_division, transformation_division)
            level = transform_level(origin_level, transformation_level)
            return division, level

        def transform(transformation: Iterable[T_StaticPosition]) -> tuple[_T_SpecialDivisionIndex, T_LevelIndex]:
            initial = None, self._DEFAULT[0]
            return functools.reduce(binary_transform, transformation, initial)

        transformations = transpose(map(parse_to_static, current))
        result = map(transform, transformations)
        return islice(chain(result, repeat(None)), note_duration)

    @typed_cache
    def resolve(
        self,
        *,
        beat: T_Positional[T_Beat],
        sustain_duration: T_Positional[T_Duration],
        note_duration: T_Positional[T_Duration],
    ) -> T_Positional[Iterable[T_PositionIndex]]:
        def convert_special(position: Iterable[_T_SpecialPositionIndex]) -> T_Positional[Iterable[T_PositionIndex]]:
            def convert_core(value: _T_SpecialPositionIndex) -> T_Positional[T_PositionIndex]:
                if is_typeform(value, tuple[Literal[True], T_LevelIndex]):
                    return T_MultiValue([(0, value[1]), (1, value[1])])
                assert is_typeform(value, T_PositionIndex), value
                return value

            return multivalue_map(lambda *x: x, *map(convert_core, position))

        out = multivalue_map(self._resolve_core, self._value, beat, sustain_duration, note_duration)
        if type(out) is not T_MultiValue:
            return convert_special(out)
        if not out:
            return self._NULL_VALUE
        return multivalue_flatten(map(convert_special, out))  # pyright complains but idk, it looks right to me...


@dataclass(kw_only=True, slots=True, frozen=True)
class NoteBlock:
    note: T_NoteValue
    instrument: str


class Instrument(
    _PositionalProperty[
        T_Instrument,
        T_Instrument,
        NoteBlock | None,
    ]
):
    _DEFAULT = "harp"
    _NULL_VALUE = None

    def _resolve_core(
        self,
        origin: T_Instrument,
        current: T_Instrument,
        note_name: str,
        transpose: _TransposeType,
    ) -> NoteBlock | None:
        def parse_relative_octave(note_name: str, default_octave: int) -> tuple[str, int]:
            if note_name.endswith("^"):
                note_name, octave = parse_relative_octave(note_name[:-1], default_octave)
                return note_name, octave + 1
            if note_name.endswith("_"):
                note_name, octave = parse_relative_octave(note_name[:-1], default_octave)
                return note_name, octave - 1
            return note_name, default_octave

        if is_typeform(note_name[-1], int, strict=False):
            note_value = NOTE_VALUE[note_name] + transpose.value
        else:
            default_octave = (INSTRUMENT_RANGE[next(strip_split(origin, "/"))].start - 6) // 12 + 2
            note, octave = parse_relative_octave(note_name, default_octave)
            note_value = NOTE_VALUE[note + str(octave)] + transpose.value

        if transpose.auto:

            def deviation(instrument: str):
                range_ = INSTRUMENT_RANGE[instrument]
                if range_.start <= note_value < range_.stop:
                    return 0
                if note_value < range_.start:
                    return 12 * math.ceil((range_.start - note_value) / 12)
                return 12 * math.floor((range_.stop - 1 - note_value) / 12)

            instrument = min(strip_split(current, "/"), key=deviation)
            instrument_range = INSTRUMENT_RANGE[instrument]
            note_value += deviation(instrument)
            return NoteBlock(note=instrument_range.index(note_value), instrument=instrument)

        for instrument in strip_split(current, "/"):
            if note_value in (instrument_range := INSTRUMENT_RANGE[instrument]):
                return NoteBlock(note=instrument_range.index(note_value), instrument=instrument)

    @typed_cache
    def resolve(
        self,
        note_name: str,
        *,
        transpose: T_Positional[_TransposeType],
    ) -> T_Positional[NoteBlock | None]:
        if note_name == "r" or _is_empty(self._value) or _is_empty(transpose):
            return self._NULL_VALUE
        return multivalue_map(self._resolve_core, self._original_value, self._value, note_name, transpose)


class Dynamic(
    _PositionalProperty[
        T_Tuple[T_Dynamic],
        T_Dynamic,
        Iterable[T_StaticAbsoluteDynamic],
    ]
):
    MAX = 6
    _DEFAULT: T_Tuple[T_StaticAbsoluteDynamic] = (1,)
    _NULL_VALUE = repeat(0)

    def _transform_core(self, current, modifier) -> T_Tuple[T_Dynamic]:
        if is_typeform(modifier, T_AbsoluteDynamic):
            return (modifier,)
        return (*current, modifier)

    def _resolve_core(
        self,
        current: T_Tuple[T_Dynamic],
        beat: T_Beat,
        sustain_duration: T_Duration,
        note_duration: T_Duration,
    ) -> Iterable[T_StaticAbsoluteDynamic]:
        # TODO: refactor, this is almost identical to SingleDivision._resolve_core
        def parse(value: T_Dynamic) -> Iterable[T_StaticDynamic]:
            def parse_timed_dynamic(timedvalue: list[T_VariableDynamic]) -> Iterable[T_StaticDynamic]:
                dynamic = timedvalue[0]
                if not dynamic.startswith(("+", "-")):
                    dynamic = int(dynamic)
                duration = parse_duration(*timedvalue[1:], beat=beat)
                if duration < 0:
                    duration += sustain_duration
                return repeat(dynamic, duration)

            if is_typeform(value, T_StaticDynamic):
                return repeat(value, sustain_duration)
            assert is_typeform(value, T_VariableDynamic), value

            tokens = strip_split(value, ",")
            timed_values = map(split_timedvalue, tokens)
            transformations = map(parse_timed_dynamic, timed_values)
            result = chain.from_iterable(transformations)
            return islice(chain(result, repeat("+0")), sustain_duration)

        def binary_transform(current: T_StaticAbsoluteDynamic, modifier: T_StaticDynamic) -> T_StaticAbsoluteDynamic:
            if is_typeform(modifier, T_StaticAbsoluteDynamic):
                return modifier
            low, high = min(1, current), self.MAX
            out = current + int(modifier)
            return min(max(out, low), high)

        def transform(transformation: Iterable[T_StaticDynamic]) -> T_StaticAbsoluteDynamic:
            return functools.reduce(binary_transform, transformation, self._DEFAULT[0])

        transformations = transpose(map(parse, current))
        result = map(transform, transformations)
        # 0 is arbitrary, dynamic doesn't matter for notes outside of sustain duration
        out = islice(chain(result, repeat(0)), note_duration)
        return deque(out)  # must exhaust the iterator to cache the result

    if TYPE_CHECKING:

        def resolve(
            self,
            *,
            beat: T_Positional[T_Beat],
            sustain_duration: T_Positional[T_Duration],
            note_duration: T_Positional[T_Duration],
        ) -> T_Positional[Iterable[T_StaticAbsoluteDynamic]]: ...


class Sustain(
    _PositionalProperty[
        T_Tuple[T_Sustain],
        T_Sustain,
        int,
    ]
):
    _DEFAULT = (-1,)

    def _transform_core(self, current, modifier) -> T_Tuple[T_Sustain]:
        if is_typeform(modifier, T_AbsoluteSustain):
            return (modifier,)
        return (*current, modifier)

    def _resolve_core(
        self,
        current: T_Tuple[T_Sustain],
        beat: T_Beat,
        note_duration: T_Duration,
    ) -> int:
        out = 1
        for sustain in current:
            relative = False
            if isinstance(sustain, bool):
                duration = note_duration if sustain else 1
            elif isinstance(sustain, int):
                duration = sustain if sustain >= 0 else note_duration + sustain
            else:
                duration = parse_duration(sustain, beat=beat)
                relative = sustain.startswith(("+", "-"))
            if relative:
                out += duration
            else:
                out = duration if duration >= 0 else note_duration + duration

        low, high = 1, note_duration
        return min(max(out, low), high)

    if TYPE_CHECKING:

        def resolve(
            self,
            *,
            beat: T_Positional[T_Beat],
            note_duration: T_Positional[T_Duration],
        ) -> T_Positional[int]: ...


@dataclass(kw_only=True, frozen=True)
class _TransposeType:
    value: int
    auto: bool


class Transpose(
    _PositionalProperty[
        _TransposeType,
        T_Transpose,
        _TransposeType,
    ]
):
    _DEFAULT = _TransposeType(value=0, auto=False)

    def _transform_core(self, current, modifier):
        if isinstance(modifier, bool):
            return _TransposeType(value=current.value, auto=modifier)
        if isinstance(modifier, int):
            return _TransposeType(value=modifier, auto=current.auto)

        if modifier.endswith(("?", "!")):
            auto = modifier.endswith("?")
            modifier = modifier[:-1]
        else:
            auto = current.auto

        if not modifier:
            value = current.value
        elif modifier.startswith("{"):
            value = int(modifier[1:-1])
        else:
            value = current.value + int(modifier)

        return _TransposeType(value=value, auto=auto)

    if TYPE_CHECKING:

        def resolve(self) -> T_Positional[_TransposeType]: ...
