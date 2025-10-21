from __future__ import annotations

import hashlib
import pickle
from humanize import naturaldelta
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

from .utils.console import Console
from platformdirs import user_cache_dir

if TYPE_CHECKING:
    from .coordinates import XYZ
    from .structure import BlockType

    class CacheType(TypedDict):
        last_modified: float
        data: dict[XYZ, BlockType]


_CACHE_MISS = object()


class Cache:
    @staticmethod
    def delete(key: str) -> None:
        try:
            get_cache_file(key).unlink()
        except Exception:
            pass

    def __init__(self, key: str):
        self.path = get_cache_file(key)
        if (cache := load_cache(self.path)) is None:
            self._data: dict[XYZ, BlockType] = {}
        else:
            self._data = cache["data"]
            delta = datetime.now() - datetime.fromtimestamp(cache["last_modified"])
            Console.info("Using cache from {time} ago.", time=naturaldelta(delta))

        self._initial_length = len(self._data)
        self._updates_count = 0

    def __setitem__(self, coords: XYZ, block: BlockType) -> None:
        self._data[coords] = block
        self._updates_count += 1

    def __getitem__(self, coords: XYZ) -> BlockType | object:
        return self._data.get(coords, _CACHE_MISS)

    def save(self):
        if not self._updates_count:
            return

        self._modified = False
        cache: CacheType = {
            "last_modified": datetime.now().timestamp(),
            "data": self._data,
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("wb") as f:
            pickle.dump(cache, f)

        Console.info("Cache saved to {path}.", path=self.path)
        if self._initial_length:
            changed_percentage = (self._updates_count / (self._initial_length)) * 100
            if changed_percentage < 0.01:
                Console.info(
                    "{count} blocks changed since last generation.",
                    count=self._updates_count,
                )
            else:
                Console.info(
                    "{count} blocks ({percentage} of cache) changed since last generation.",
                    count=self._updates_count,
                    percentage=f"{changed_percentage:.2f}%",
                )


def get_cache_file(key: str) -> Path:
    file_name = hashlib.sha256(key.encode()).hexdigest()[:16]
    return Path(user_cache_dir("noteblock-generator")) / file_name


def load_cache(path: Path) -> CacheType | None:
    try:
        with path.open("rb") as f:
            return pickle.load(f)
    except Exception:
        return None
