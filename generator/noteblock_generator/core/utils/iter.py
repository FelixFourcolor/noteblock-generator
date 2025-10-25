from __future__ import annotations

from collections import deque
from itertools import chain
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def exhaust(*iterables: Iterable) -> None:
    deque(chain(*iterables), maxlen=0)
