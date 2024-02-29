from __future__ import annotations

import functools
import re
from itertools import repeat
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, TypeGuard, TypeVar

from pydantic import TypeAdapter, ValidationError

from .typedefs import T_Beat, T_Duration, T_MultiValue, T_Positional

T = TypeVar("T")
CT = TypeVar("CT", bound=Callable)


def cache(func: CT) -> CT:
    if TYPE_CHECKING:
        return func
    return functools.cache(func)


def flatten(nested_list: Iterable[T | T_MultiValue[T]]) -> T_MultiValue:
    def core() -> Iterator[T]:
        for i in nested_list:
            if isinstance(i, T_MultiValue):
                yield from i
            else:
                yield i

    return T_MultiValue(core())


@cache
def is_typeform(obj: Any, typeform: type[T]) -> TypeGuard[T]:
    try:
        TypeAdapter(typeform).validate_python(obj)
        return True
    except ValidationError:
        return False


@cache
def parse_timedvalue(value: str) -> list[str]:
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
        tmp = parse_duration(duration[:-1], beat=beat)
        if (out := int(tmp * 1.5)) == tmp * 1.5:
            return out
        raise ValueError("Cannot apply dotted rhythm to this note")  # TODO: error handling
    if duration.endswith("b"):
        return beat * int(duration[:-1])
    else:
        return int(duration)


def strip_split(string: str, delimiter: str):
    return filter(bool, map(str.strip, string.split(delimiter)))


def positional_map(func: Callable[..., T], *args: T_Positional[Any], **kwargs: T_Positional[Any]) -> T_Positional[T]:
    any_multivalued_args = any(isinstance(arg, T_MultiValue) for arg in args)
    zipped_args = zip(*(arg if isinstance(arg, T_MultiValue) else repeat(arg) for arg in args))

    multivalued_kwargs = {k: v for k, v in kwargs.items() if isinstance(v, T_MultiValue)}
    single_kwargs = {k: v for k, v in kwargs.items() if k not in multivalued_kwargs}

    if not multivalued_kwargs:
        if not any_multivalued_args:
            return func(*args, **kwargs)
        return T_MultiValue(func(*arg, **kwargs) for arg in zipped_args)

    zipped_kwargs = map(dict, map(functools.partial(zip, multivalued_kwargs.keys()), zip(*multivalued_kwargs.values())))
    if not any_multivalued_args:
        return T_MultiValue(func(*args, **single_kwargs, **kwarg) for kwarg in zipped_kwargs)
    return T_MultiValue(func(*arg, **single_kwargs, **kwarg) for arg, kwarg in zip(zipped_args, zipped_kwargs))
