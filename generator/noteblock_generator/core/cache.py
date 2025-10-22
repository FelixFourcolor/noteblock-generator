from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from humanize import naturaldelta
from msgspec import Struct, msgpack
from platformdirs import user_cache_dir

from ..api.types import NullableBlockData
from .coordinates import XYZ
from .utils.console import Console


class CacheData(Struct):
    last_modified: float
    blocks: dict[XYZ, NullableBlockData]


_CACHE_MISS = object()


class BlocksCache:
    @staticmethod
    def delete(key: str) -> None:
        try:
            get_cache_file(key).unlink()
        except Exception:
            pass

    def __init__(self, key: str):
        self.path = get_cache_file(key)

        if cache := load_cache(self.path):
            self._data = cache
            delta = datetime.now() - datetime.fromtimestamp(cache.last_modified)
            Console.info("Using cache from {time} ago.", time=naturaldelta(delta))
        else:
            self._data = CacheData(last_modified=0, blocks={})

        self._initial_length = len(self._data.blocks)
        self._updates_count = 0

    def __setitem__(self, coords: XYZ, block: NullableBlockData) -> None:
        self._data.blocks[coords] = block
        self._updates_count += 1

    def __getitem__(self, coords: XYZ) -> NullableBlockData | object:
        return self._data.blocks.get(coords, _CACHE_MISS)

    def save(self):
        if not self._updates_count:
            return

        self._data.last_modified = datetime.now().timestamp()
        save_cache(self.path, self._data)

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
    file_name = hashlib.sha256(key.encode()).hexdigest()[:24]
    return Path(user_cache_dir("noteblock-generator")) / file_name


def load_cache(path: Path) -> CacheData | None:
    try:
        with path.open("rb") as f:
            return msgpack.decode(f.read(), type=CacheData)
    except Exception:
        return None


def save_cache(path: Path, cache: CacheData) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(msgpack.encode(cache))
