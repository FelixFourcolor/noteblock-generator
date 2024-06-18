from __future__ import annotations

import functools
import math
import re
from abc import ABC, abstractmethod
from collections import deque
from copy import copy as shallowcopy
from dataclasses import dataclass
from itertools import chain, islice, repeat
from typing import Generic, Hashable, Iterable, Literal, Protocol, TypeVar, cast, final

from .data import INSTRUMENT_RANGE, NOTE_VALUE
from .utils import (
    cache,
    extend,
    is_typeform,
    multivalue_flatten,
    multivalue_map,
    parse_duration,
    split_timedvalue,
    strip_split,
    transpose,
)
from .validator import (
    T_Beat,
    T_BeatRate,
    T_CompoundPosition,
    T_Delete,
    T_Division,
    T_Duration,
    T_Dynamic,
    T_Instrument,
    T_MultiValue,
    T_Name,
    T_NamedEnvironment,
    T_Position,
    T_Positional,
    T_PositionalProperty,
    T_Reset,
    T_StaticAbsoluteDynamic,
    T_StaticAbsoluteLevel,
    T_StaticCompoundPosition,
    T_StaticDynamic,
    T_StaticLevel,
    T_StaticPosition,
    T_StaticProperty,
    T_StaticRelativeLevel,
    T_Sustain,
    T_Tempo,
    T_TickRate,
    T_Time,
    T_Transpose,
    T_TrillStyle,
    T_VariableCompoundPosition,
    T_VariableDynamic,
    T_VariableLevel,
    Tuple,
)


class P_Named(Protocol):
    children_count: int
    name: Name


def _get_name(index: int | tuple[int, int], src: T_NamedEnvironment):
    if (name := src.name) is not None:
        return name.replace(" ", "_")
    if (path := src.path) is not None:
        return path.stem.replace(" ", "_")
    env_type = type(src).__name__[2:]  # every env type name starts with "T_" (see validator.py), remove it
    return f"{env_type}_{index}"


class Name:
    def __init__(self):
        self._envs: Tuple[P_Named] = ()
        self._names: Tuple[str] = ()

    def transform(self, index: int | tuple[int, int], src: T_NamedEnvironment, env: P_Named) -> Name:
        self = shallowcopy(self)
        self._envs = (*self._envs, env)
        self._names = (*self._names, _get_name(index, src))
        return self

    def resolve(self) -> T_Name:
        # Skip components whose parent has <2 children,
        # e.g. if the full name is "/my_symphony/movement_1/violin_I",
        # but "my_symphony" is the only composition and "movement_1" is the only movement,
        # the resolved name will just be "violin_I".
        return "/".join(name for (env, name) in zip(self._envs[:-1], self._names[1:]) if env.children_count > 1)


S = TypeVar("S")
T = TypeVar("T", bound=Hashable)
U = TypeVar("U", bound=Hashable)
V = TypeVar("V")


class _StaticProperty(
    Generic[
        T,  # `transform` argument type
        V,  # `resolve` output type
    ]
):
    _value: T
    _anchored_value: T
    _DEFAULT: T

    def __init__(self):
        self._value = self._anchored_value = self._DEFAULT

    def anchor(self, modifier: T = None):
        if modifier is None:
            self._anchored_value = self._value
        else:
            self._anchored_value = modifier

    @cache
    def transform(self, modifier: T_StaticProperty[T]):
        self = shallowcopy(self)
        if modifier is not None:
            if modifier == "$reset":
                self._value = self._anchored_value
            else:
                self._value = cast(T, modifier)
        return self

    def resolve(self) -> V:
        return cast(V, self._value)


class Time(_StaticProperty[T_Time, int]):
    _DEFAULT = 16

    def resolve(self, *, beat: T_Beat) -> int:
        if isinstance(self._value, int):
            return self._value
        return parse_duration(*split_timedvalue(self._value), beat=beat)


class Tempo(_StaticProperty[T_Tempo, T_TickRate]):
    _DEFAULT = (150, "bpm")

    def resolve(self, *, beat: T_Beat) -> T_TickRate:
        if isinstance(value := self._value, tuple):
            value = value[0]
        if is_typeform(value, T_TickRate):
            return value
        assert is_typeform(value, T_BeatRate)
        GAME_TICKS_PER_REDSTONE_TICK = 2
        return value * GAME_TICKS_PER_REDSTONE_TICK * beat / 60


class Beat(_StaticProperty[T_Beat, T_Beat]):
    _DEFAULT = 4


class TrillStyle(_StaticProperty[T_TrillStyle, T_TrillStyle]):
    _DEFAULT = "normal"


class _PositionalProperty(
    ABC,
    Generic[
        U,  # `transform` argument type
        V,  # `resolve` output type
    ],
):
    _DEFAULT: Tuple[U] = ()
    _NULL_VALUE: T_Positional[V] = T_MultiValue()
    _anchored_value: T_Positional[Tuple[U]]
    _value: T_Positional[Tuple[U]]

    @final
    def __init__(self):
        self._value = self._anchored_value = self._DEFAULT

    @final
    def anchor(self, modifier: U = None):
        if modifier is not None:
            self._value = multivalue_map(lambda x, y: (y, *x), self._value, modifier)
        self._anchored_value = self._value

    @final
    def _transform_core(
        self,
        anchor: Tuple[U],
        data: Tuple[U],
        modifier: U | T_Reset | T_Delete | None,
    ) -> Tuple[U] | None:
        if modifier is None:
            return data
        if modifier == "$reset":
            return anchor
        if modifier == "$del":
            return None
        return (*data, modifier)

    @final
    def _prepare_modifier(self, modifier: T_PositionalProperty[U]) -> T_PositionalProperty[U]:
        if type(modifier) is not T_MultiValue:
            return modifier

        modifier_len = len(modifier)
        working_modifier = list(modifier)  # convert to list to allow mutation

        if type(self._value) is T_MultiValue:
            current_len = len(self._value)
            # fewer modifiers than current values -> implicit delete
            if modifier_len < current_len:
                working_modifier.extend(repeat("$del", current_len - modifier_len))
            # more modifiers than current values -> apply extra modifiers to _DEFAULT
            elif modifier_len > current_len:
                self._value += repeat(self._DEFAULT, modifier_len - current_len)

        def replace(iterable: Iterable[S], old: S, new: S) -> Iterable[S]:
            for element in iterable:
                if element == old:
                    yield new
                else:
                    yield element

        if type(self._anchored_value) is T_MultiValue:
            original_len = len(self._anchored_value)
            # replace every "$reset" modifier with "$del" if it overflows original value
            if modifier_len > original_len:
                inbound_modifiers = working_modifier[:original_len]
                outbound_modifiers = replace(working_modifier[original_len:], "$reset", "$del")
                working_modifier = chain(inbound_modifiers, outbound_modifiers)

        return T_MultiValue(working_modifier)  # type: ignore  # no idea why pyright complains

    @final
    def transform(self, modifier: T_PositionalProperty[U]):
        self = shallowcopy(self)
        modifier = self._prepare_modifier(modifier)

        new_value = multivalue_map(self._transform_core, self._anchored_value, self._value, modifier)
        if type(new_value) is T_MultiValue:
            self._value = T_MultiValue(e for e in new_value if e is not None)
        elif new_value is None:
            self._value = T_MultiValue()
        else:
            self._value = new_value
        return self

    @abstractmethod
    def _resolve_core(self, data: Tuple[U]) -> V: ...

    @abstractmethod
    def resolve(self, *args, **kwargs) -> T_Positional[V]:
        out = multivalue_map(self._resolve_core, self._value, *args, **kwargs)
        if type(out) is T_MultiValue and not out:
            return self._NULL_VALUE
        return out


P_Level = int
P_Division = Literal[0, 1]
P_Position = tuple[P_Division | None, P_Level]

# temp position is to handle "LR" (bothsides) division
# it's internally stored as a magic value (`Literal["bothsides"]`), then resolve() converts it to the proper format
_P_TempDivision = P_Division | None | Literal["bothsides"]
_P_TempPosition = tuple[_P_TempDivision, P_Level]


class Position(_PositionalProperty[T_Position, Iterable[P_Position]]):
    _DEFAULT: Tuple[T_StaticAbsoluteLevel] = ()
    _NULL_VALUE: Iterable[tuple[None, Literal[0]]] = repeat((None, 0))

    def _resolve_core(
        self,
        data: Tuple[T_Position],
        *,
        beat: T_Beat,
        sustain_duration: T_Duration,
        note_duration: T_Duration,
    ) -> Iterable[_P_TempPosition]:
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
            current: tuple[_P_TempDivision, P_Level],
            modifier: T_StaticPosition,
        ) -> tuple[_P_TempDivision, P_Level]:
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

            def transform_division(current: _P_TempDivision, modifier: T_Division | None):
                if modifier is None:  # no changes
                    return current
                if modifier == "SW":
                    if current in (0, 1):
                        return (current + 1) % 2
                    return current
                if modifier == "M":
                    return None
                if modifier == "LR":
                    return "bothsides"
                return cast(Literal[0, 1], ["L", "R"].index(modifier))

            def transform_level(current: int, modifier: T_StaticLevel | None) -> P_Level:
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

        def transform(transformation: Iterable[T_StaticPosition]) -> tuple[_P_TempDivision, P_Level]:
            if type(self._anchored_value) is T_MultiValue:
                initial = None, self._anchored_value[0][0]
            else:
                initial = None, self._anchored_value[0]
            assert is_typeform(initial, tuple[_P_TempDivision, P_Level])
            return functools.reduce(binary_transform, transformation, initial)

        transformations = transpose(map(parse_to_static, data))
        result = map(transform, transformations)
        return islice(extend(result), note_duration)

    @cache
    def resolve(
        self,
        *,
        beat: T_Positional[T_Beat],
        sustain_duration: T_Positional[T_Duration],
        note_duration: T_Positional[T_Duration],
    ) -> T_Positional[Iterable[P_Position]]:
        def handle_temp_position(position: Iterable[_P_TempPosition]) -> T_Positional[Iterable[P_Position]]:
            def core(value: _P_TempPosition) -> T_Positional[P_Position]:
                if is_typeform(value, tuple[Literal["bothsides"], P_Level]):
                    return T_MultiValue([(0, value[1]), (1, value[1])])
                assert is_typeform(value, P_Position), value
                return value

            return multivalue_map(lambda *x: x, *map(core, position))

        out = multivalue_map(
            self._resolve_core,
            self._value,
            beat=beat,
            sustain_duration=sustain_duration,
            note_duration=note_duration,
        )
        if type(out) is not T_MultiValue:
            return handle_temp_position(out)
        if not out:
            return self._NULL_VALUE
        return multivalue_flatten(map(handle_temp_position, out))  # type: ignore  # no idea why pyright complains


@dataclass(kw_only=True, slots=True, frozen=True)
class NoteBlock:
    note: int
    instrument: str


class Instrument(
    _PositionalProperty[
        T_Instrument,
        NoteBlock | None,
    ]
):
    _DEFAULT = ("harp",)
    _NULL_VALUE = None

    def _resolve_core(
        self,
        data: Tuple[T_Instrument],
        *,
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

        origin = data[0]
        current = data[-1]

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

    @cache
    def resolve(
        self,
        *,
        note_name: str,
        transpose: T_Positional[_TransposeType],
    ) -> T_Positional[NoteBlock | None]:
        if note_name == "r":
            return self._NULL_VALUE
        return super().resolve(note_name=note_name, transpose=transpose)


class Dynamic(_PositionalProperty[T_Dynamic, Iterable[T_StaticAbsoluteDynamic]]):
    MAX = 6
    _DEFAULT: Tuple[T_StaticAbsoluteDynamic] = (1,)
    _NULL_VALUE = repeat(0)

    def _resolve_core(
        self,
        data: Tuple[T_Dynamic],
        *,
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
            return functools.reduce(binary_transform, transformation, 1)

        transformations = transpose(map(parse, data))
        result = map(transform, transformations)
        out = islice(extend(result), note_duration)
        return deque(out)  # must exhaust the iterator to cache the result

    @cache
    def resolve(
        self,
        *,
        beat: T_Positional[T_Beat],
        sustain_duration: T_Positional[T_Duration],
        note_duration: T_Positional[T_Duration],
    ) -> T_Positional[Iterable[T_StaticAbsoluteDynamic]]:
        return super().resolve(beat=beat, sustain_duration=sustain_duration, note_duration=note_duration)


class Sustain(_PositionalProperty[T_Sustain, int]):
    _DEFAULT = (-1,)

    def _resolve_core(
        self,
        data: Tuple[T_Sustain],
        *,
        beat: T_Beat,
        note_duration: T_Duration,
    ) -> int:
        out = 1
        for sustain in data:
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

    @cache
    def resolve(
        self,
        *,
        beat: T_Positional[T_Beat],
        note_duration: T_Positional[T_Duration],
    ) -> T_Positional[int]:
        return super().resolve(beat=beat, note_duration=note_duration)


@dataclass(kw_only=True, frozen=True)
class _TransposeType:
    value: int
    auto: bool


class Transpose(_PositionalProperty[T_Transpose, _TransposeType]):
    _DEFAULT = (0,)

    def _resolve_core(self, data: Tuple[T_Transpose]) -> _TransposeType:
        def binary_transform(current: _TransposeType, modifier: T_Transpose) -> _TransposeType:
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

        initial = _TransposeType(value=0, auto=False)
        return functools.reduce(binary_transform, data, initial)

    @cache
    def resolve(self) -> T_Positional[_TransposeType]:
        return super().resolve()
