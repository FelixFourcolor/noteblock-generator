from __future__ import annotations

import functools
import re
from contextlib import suppress
from itertools import repeat
from typing import TYPE_CHECKING, Any, Callable, Hashable, Iterable, Iterator, TypeGuard, TypeVar

from pydantic import TypeAdapter, ValidationError

from .validator import T_Beat, T_Duration, T_MultiValue, T_Positional

S = TypeVar("S")
T = TypeVar("T")
U = TypeVar("U")
CT = TypeVar("CT", bound=Callable)


def cache(func: CT) -> CT:
    if TYPE_CHECKING:
        return func
    return functools.cache(func)


@cache
def is_typeform(obj: Hashable, typeform: type[T], *, strict=True) -> TypeGuard[T]:
    with suppress(ValidationError):
        TypeAdapter(typeform).validate_python(obj, strict=strict)
        return True
    return False


def multivalue_flatten(nested_iterable: Iterable[T_Positional[T]]) -> T_MultiValue[T]:
    def flatten_core() -> Iterator[T]:
        for i in nested_iterable:
            if type(i) is T_MultiValue:
                yield from i
            else:
                yield i

    return T_MultiValue(flatten_core())


@cache
def split_timedvalue(value: str) -> list[str]:
    def append(element: str):
        if element:
            out.append(element)

    out: list[str] = []
    last_match_index = 0
    for match_index in map(re.Match.start, re.finditer("\\s+[+-]?|\\s*[+-]", value)):
        append(value[last_match_index:match_index].strip())
        last_match_index = match_index
    append(value[last_match_index:].strip())
    return out


@cache
def parse_duration(*durations: str, beat: T_Beat) -> T_Duration:
    if not durations:
        return beat

    if len(durations) > 1:
        return sum(map(functools.partial(parse_duration, beat=beat), durations))

    if not (duration := durations[0]):
        return beat

    if duration.startswith("-"):
        return -parse_duration(duration[1:], beat=beat)
    if duration.endswith("."):
        return int(1.5 * parse_duration(duration[:-1], beat=beat))
    if duration.endswith("b"):
        return beat * int(duration[:-1])
    return int(duration)


def strip_split(string: str, delimiter: str):
    return filter(None, map(str.strip, string.split(delimiter)))


def multivalue_map(func: Callable[..., T], *args: T_Positional[Any], **kwargs: T_Positional[Any]) -> T_Positional[T]:
    single_kwargs = {k: v for k, v in kwargs.items() if type(v) is not T_MultiValue}
    multi_kwargs = {k: v for k, v in kwargs.items() if k not in single_kwargs}
    zipped_kwargs = map(dict, map(functools.partial(strict_zip, multi_kwargs.keys()), transpose(multi_kwargs.values())))

    multi_args = [arg for arg in args if type(arg) is T_MultiValue]
    if not multi_args:
        if not multi_kwargs:
            return func(*args, **kwargs)
        return T_MultiValue(func(*args, **single_kwargs, **kwarg) for kwarg in zipped_kwargs)

    zipped_args = transpose(arg if arg in multi_args else repeat(arg, len(multi_args[0])) for arg in args)
    if not multi_kwargs:
        return T_MultiValue(func(*arg, **kwargs) for arg in zipped_args)
    return T_MultiValue(func(*arg, **single_kwargs, **kwarg) for arg, kwarg in strict_zip(zipped_args, zipped_kwargs))


strict_zip = functools.partial(zip, strict=True)


def transpose(double_iterable: Iterable[Iterable[T]]) -> Iterable[Iterable[T]]:
    return strict_zip(*double_iterable)


class MultiSet(dict[S, list[T]]):
    def __init__(self, iterable: Iterable[T], predicate: Callable[[T], S]):
        for elem in iterable:
            if (value := predicate(elem)) in self:
                self[value].append(elem)
            else:
                self[value] = [elem]

    def flatten(self) -> Iterator[T]:
        for key in self.keys():
            yield from self[key]
