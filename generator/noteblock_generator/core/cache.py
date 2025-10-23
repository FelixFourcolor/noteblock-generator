from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from humanize import naturaltime
from msgspec import Struct, msgpack
from platformdirs import user_cache_dir

from noteblock_generator import APP_NAME

from ..api.types import BlockType
from .coordinates import XYZ
from .utils.console import Console


class CacheData(Struct):
    last_modified: float = datetime.now().timestamp()
    blocks: dict[XYZ, BlockType | None] = {}


_CACHE_MISS = object()


class Cache:
    def __init__(self, key: object, *, enabled: bool):
        self.enabled = enabled
        self._path = _get_cache_file(str(key))
        self._initial_length = 0

    @property
    def has_data(self):
        return bool(self._initial_length)

    def __enter__(self):
        if not self.enabled:
            self._path.unlink(missing_ok=True)
            return None

        self._load()
        self._initial_length = len(self._data.blocks)
        self._updates_count = 0
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self.enabled and not exc_type:
            self._save()

    def __setitem__(self, coords: XYZ, block: BlockType | None) -> None:
        self._data.blocks[coords] = block
        self._updates_count += 1

    def __getitem__(self, coords: XYZ) -> object:
        return self._data.blocks.get(coords, _CACHE_MISS)

    def display_stats(self):
        if not self._updates_count:
            Console.info(
                "Structure unchanged; nothing to generate.",
                important=True,
            )
            return

        if not self._initial_length:
            # should never happen, but just in case
            return

        percentage = (self._updates_count / (self._initial_length)) * 100
        Console.info(
            "Structure differs by {difference} from last generation.",
            difference=f"{percentage:.2f}%"
            if percentage > 0.01
            else f"{self._updates_count} blocks",
            important=True,
        )

    def _load(self):
        if cache := _load_cache(self._path):
            self._data = cache
            delta = datetime.now() - datetime.fromtimestamp(cache.last_modified)
            Console.info(
                "Found previous generation {whence}", whence=naturaltime(delta)
            )
        else:
            self._data = CacheData()
            Console.info(
                "No previous generation found; generating from scratch", important=True
            )

    def _save(self):
        if not self._updates_count:
            return

        self._data.last_modified = datetime.now().timestamp()
        _save_cache(self._path, self._data)


def _get_cache_file(key: str) -> Path:
    file_name = hashlib.sha256(key.encode()).hexdigest()[:24]
    cache_dir = Path(user_cache_dir(APP_NAME))
    return cache_dir / file_name


def _load_cache(path: Path) -> CacheData | None:
    try:
        with path.open("rb") as f:
            return msgpack.decode(f.read(), type=CacheData)
    except Exception:
        return None


def _save_cache(path: Path, cache: CacheData) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(msgpack.encode(cache))
