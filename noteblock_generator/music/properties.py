from __future__ import annotations

import contextlib
import re
from copy import copy as shallowcopy
from dataclasses import dataclass
from functools import reduce
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Generic, Hashable, Iterable, Protocol, TypeVar, cast

from .typedefs import (
    T_AbsoluteDynamic,
    T_AbsoluteLevel,
    T_AbsoluteSustain,
    T_AbsoluteTranspose,
    T_Array,
    T_Beat,
    T_CompoundPosition,
    T_Delay,
    T_Delete,
    T_Division,
    T_DivisionIndex,
    T_DoubleIndex,
    T_Duration,
    T_Dynamic,
    T_Index,
    T_Instrument,
    T_Level,
    T_LevelIndex,
    T_MultiValue,
    T_Name,
    T_NoteValue,
    T_Position,
    T_Positional,
    T_PositionalProperty,
    T_RelativeLevel,
    T_Reset,
    T_SingleDivisionPosition,
    T_StaticAbsoluteDynamic,
    T_StaticDynamic,
    T_StaticProperty,
    T_Sustain,
    T_Tick,
    T_Time,
    T_Transpose,
    T_TrillStyle,
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
    transpose,
    typed_cache,
)


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
        return f"{type(src).__name__} {index}"

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


class _PositionalProperty(
    Generic[
        T,  # internal representation type
        U,  # `transform` argument type
        V,  # `resolve` output type
    ]
):
    _DEFAULT: T
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

    def _transform_core_wrapper(self, origin: T, current: T, modifier: U | T_Reset | T_Delete | None) -> T | None:
        if modifier is None:
            return current
        if modifier == "$reset":
            return origin
        if modifier == "$del":
            return None
        return self._transform_core(current, modifier)

    def _prepare_transform(self, modifier: T_PositionalProperty[U]) -> T_PositionalProperty[U]:
        if not isinstance(modifier, T_MultiValue):
            return modifier

        modifier_len = len(modifier)
        working_modifier = list(modifier)  # convert to list to allow mutation

        if isinstance(self._value, T_MultiValue):
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

        if isinstance(self._original_value, T_MultiValue):
            original_len = len(self._original_value)
            # replace every "$reset" modifier with "$del" if it overflows original value
            if modifier_len > original_len:
                inbound_modifiers = working_modifier[:original_len]
                outbound_modifiers = replace(working_modifier[original_len:], "$reset", "$del")
                working_modifier = inbound_modifiers + list(outbound_modifiers)

        return T_MultiValue(working_modifier)  # type: ignore # no idea why pyright complains

    @typed_cache
    def transform(self, modifier: T_PositionalProperty[U], *, save=False):
        self = shallowcopy(self)
        modifier = self._prepare_transform(modifier)

        new_value = positional_map(self._transform_core_wrapper, self._original_value, self._value, modifier)
        if isinstance(new_value, T_MultiValue):
            new_value = T_MultiValue(cast(T, e) for e in new_value if e is not None)
            if new_value:
                self._value = new_value
            else:
                self._value = self._DEFAULT
        elif new_value is None:
            self._value = self._DEFAULT
        else:
            self._value = new_value
        if save:
            self._original_value = self._value
        return self

    @typed_cache
    def resolve(self, *args, **kwargs) -> T_Positional[V]:
        return positional_map(self._resolve_core, self._value, *args, **kwargs)


class GlobalPosition(
    _PositionalProperty[T_Array[T_Position], T_Position, T_Array[T_Position]],
):
    _DEFAULT = ()

    def __init__(self):
        self._value = self._original_value = self._DEFAULT

    def _transform_core(self, current, modifier) -> T_Array[T_Position]:
        if is_typeform(modifier, T_AbsoluteLevel):
            return (modifier,)
        return (*current, modifier)

    if TYPE_CHECKING:

        def resolve(self) -> T_Positional[T_Array[T_Position]]: ...


class _LocalPosition:
    def apply_globals(self, modifier: GlobalPosition):
        self = shallowcopy(self)

        def apply(self, modifier: T_Array[T_Position]):
            for mod in modifier:
                self = _PositionalProperty.transform(self, mod)
            return self._value

        self._value = positional_map(apply, self, modifier.resolve())
        return self


class SingleDivisionPosition(
    _LocalPosition,
    _PositionalProperty[T_LevelIndex, T_SingleDivisionPosition, T_LevelIndex],
):
    def __init__(self, index: T_LevelIndex):
        self._value = self._original_value = self._DEFAULT = index

    def _transform_core(self, current, modifier) -> T_LevelIndex:
        if is_typeform(modifier, T_AbsoluteLevel):
            return modifier
        assert is_typeform(modifier, T_RelativeLevel), modifier
        return current + int(modifier)

    if TYPE_CHECKING:

        def resolve(self) -> T_Positional[T_LevelIndex]: ...


class DoubleDivisionPosition(
    _LocalPosition,
    _PositionalProperty[T_Index, T_Position, T_DoubleIndex],
):
    def __init__(self, index: T_LevelIndex):
        self._value = self._original_value = self._DEFAULT = index

    def _split_division_and_level(self, value: T_CompoundPosition) -> tuple[T_Division, T_Level]:
        match = re.search("left|right|switch", value)
        assert match is not None, match  # match is guaranteed by T_CompoundPosition type
        division = cast(T_Division, match.group())
        level = value[match.end() :].strip()
        return division, level

    def _transform_division(self, current: T_DivisionIndex | None, modifier: T_Division | None):
        if modifier is None:
            return current
        if modifier == "switch":
            if current is None:
                return None
            return (current + 1) % 2
        if modifier == "bothsides":
            return None
        return cast(T_DivisionIndex, ["left", "right"].index(modifier))

    def _transform_level(self, current: T_LevelIndex, modifier: T_Level | None) -> T_LevelIndex:
        if modifier is None:
            return current
        if is_typeform(modifier, T_AbsoluteLevel):
            return modifier
        return current + int(modifier)

    def _transform_core(self, current, modifier) -> T_Index:
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
            transformation_division, transformation_level = self._split_division_and_level(modifier)
        # ---
        division = self._transform_division(origin_division, transformation_division)
        level = self._transform_level(origin_level, transformation_level)
        if division is None:
            return level
        return division, level

    @typed_cache
    def resolve(self) -> T_Positional[T_DoubleIndex]:
        def handle_bothsides(current: T_Index) -> T_Positional[T_DoubleIndex]:
            if isinstance(current, T_LevelIndex):
                return T_MultiValue(((0, current), (1, current)))
            return current

        if isinstance(self._value, T_MultiValue):
            return mutivalue_flatten(map(handle_bothsides, self._value))
        return handle_bothsides(self._value)


@dataclass(kw_only=True, slots=True, frozen=True)
class NoteBlock:
    note: T_NoteValue
    instrument: str


class Instrument(_PositionalProperty[T_Instrument, T_Instrument, NoteBlock]):
    _DEFAULT = "harp"

    def _resolve_core(
        self,
        origin: T_Instrument,
        current: T_Instrument,
        note_name: str,
        transpose: T_AbsoluteTranspose,
    ):
        def parse_relative_octave(note_name: str, default_octave: int) -> tuple[str, int]:
            if note_name.endswith("^"):
                note_name, octave = parse_relative_octave(note_name[:-1], default_octave)
                return note_name, octave + 1
            if note_name.endswith("_"):
                note_name, octave = parse_relative_octave(note_name[:-1], default_octave)
                return note_name, octave - 1
            return note_name, default_octave

        if is_typeform(note_name[-1], int, strict=False):
            note_value = _NOTE_VALUE[note_name] + transpose
        else:
            default_octave = (_INSTRUMENT_RANGE[next(strip_split(origin, "/"))].start - 6) // 12 + 2
            note, octave = parse_relative_octave(note_name, default_octave)
            note_value = _NOTE_VALUE[note + str(octave)] + transpose

        for instrument in strip_split(current, "/"):
            instrument_range = _INSTRUMENT_RANGE[instrument]  # guarantee valid key by T_Instrument
            with contextlib.suppress(ValueError):
                return NoteBlock(note=instrument_range.index(note_value), instrument=instrument)

        if transpose < 0:
            str_transpose = str(transpose)
        elif transpose == 0:
            str_transpose = ""
        else:
            str_transpose = f"+{transpose}"
        raise ValueError(f"{note_name}{str_transpose} is out of range for {current}")

    @typed_cache
    def resolve(self, note_name: str, transpose: T_Positional[T_AbsoluteTranspose]) -> T_Positional[NoteBlock]:
        return positional_map(self._resolve_core, self._original_value, self._value, note_name, transpose)


class Dynamic(
    _PositionalProperty[T_Array[T_Dynamic], T_Dynamic, list[T_StaticAbsoluteDynamic]],
):
    _DEFAULT = (1,)

    def _transform_core(self, current, modifier) -> T_Array[T_Dynamic]:
        if is_typeform(modifier, T_AbsoluteDynamic):
            return (modifier,)
        return (*current, modifier)

    def _resolve_core(
        self,
        current: T_Array[T_Dynamic],
        beat: T_Beat,
        sustain_duration: T_Duration,
        note_duration: T_Duration,
    ):
        def parse(value: T_Dynamic) -> list[T_StaticDynamic]:
            if is_typeform(value, T_StaticDynamic):
                return [value] * sustain_duration
            assert is_typeform(value, T_VariableDynamic), value

            def parse_variable_dynamic(tokens: list[T_VariableDynamic]) -> list[T_StaticDynamic]:
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

        def transform2(current: T_StaticAbsoluteDynamic, modifier: T_StaticDynamic) -> T_StaticAbsoluteDynamic:
            if is_typeform(modifier, T_StaticAbsoluteDynamic):
                return modifier
            low, high = min(1, current), 4
            out = current + int(modifier)
            return min(max(out, low), high)

        def transform(transformation: Iterable[T_StaticDynamic]):
            return reduce(transform2, transformation, 1)

        transformations = transpose(map(parse, current))
        result = list(map(transform, transformations))
        padding = [0 for _ in range(note_duration - sustain_duration)]
        return result + padding

    if TYPE_CHECKING:

        def resolve(
            self,
            beat: T_Positional[T_Beat],
            sustain_duration: T_Positional[T_Duration],
            note_duration: T_Positional[T_Duration],
        ) -> T_Positional[list[T_StaticAbsoluteDynamic]]: ...


class Sustain(_PositionalProperty[T_Array[T_Sustain], T_Sustain, int]):
    _DEFAULT = (-1,)

    def _transform_core(self, current, modifier) -> T_Array[T_Sustain]:
        if is_typeform(modifier, T_AbsoluteSustain):
            return (modifier,)
        return (*current, modifier)

    def _resolve_core(
        self,
        current: T_Array[T_Sustain],
        beat: T_Beat,
        note_duration: T_Duration,
    ) -> int:
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

        low, high = 1, note_duration
        return min(max(out, low), high)

    if TYPE_CHECKING:

        def resolve(
            self,
            beat: T_Positional[T_Beat],
            note_duration: T_Positional[T_Duration],
        ) -> T_Positional[int]: ...


class Transpose(_PositionalProperty[T_AbsoluteTranspose, T_Transpose, T_AbsoluteTranspose]):
    _DEFAULT = 0

    def _transform_core(self, current, modifier):
        if isinstance(modifier, T_AbsoluteTranspose):
            return modifier
        return current + int(modifier)

    if TYPE_CHECKING:

        def resolve(self) -> T_Positional[T_AbsoluteTranspose]: ...


def _generate_note_values():
    notes = ["c", "cs", "d", "ds", "e", "f", "fs", "g", "gs", "a", "as", "b"]
    octaves = {1: {note: value for value, note in enumerate(notes)}}
    for name, value in dict(octaves[1]).items():
        octaves[1][name + "s"] = value + 1
        if not name.endswith("s"):
            octaves[1][name + "b"] = value - 1
            octaves[1][name + "bb"] = value - 2
    for i in range(1, 7):
        octaves[i + 1] = {note: value + 12 for note, value in octaves[i].items()}
    return {note + str(octave): value for octave, notes in octaves.items() for note, value in notes.items()}


_NOTE_VALUE = _generate_note_values()
_INSTRUMENT_RANGE = {
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
