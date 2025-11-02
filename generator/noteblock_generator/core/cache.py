from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import final

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


@final
class Cache:
    @staticmethod
    def delete(world_path: Path) -> None:
        path = _get_cache_file(world_path)
        path.unlink(missing_ok=True)

    def __init__(self, world_path: Path):
        self._world_path = world_path
        if cache := _load_cache(self._world_path):
            self._data = cache
            delta = datetime.now() - datetime.fromtimestamp(cache.last_modified)
            Console.info(
                "Using previous generation from {whence}", whence=naturaltime(delta)
            )
        else:
            self._data = CacheData()
            Console.warn(
                "No previous generation found. This run will generate from scratch."
            )
        self._initial_length = len(self._data.blocks)
        self._updates_count = 0

    @property
    def has_data(self):
        return bool(self._initial_length)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if not exc_type:
            self._data.last_modified = datetime.now().timestamp()
            _save_cache(self._world_path, self._data)

    def __setitem__(self, coords: XYZ, block: BlockType | None) -> None:
        self._data.blocks[coords] = block
        self._updates_count += 1

    def __getitem__(self, coords: XYZ) -> object:
        return self._data.blocks.get(coords, _CACHE_MISS)

    def display_stats(self):
        if not self._updates_count:
            Console.success("Structure unchanged; nothing to generate.")
            return

        if not self._initial_length:  # should never happen, but just in case
            return

        percentage = (self._updates_count / (self._initial_length)) * 100
        blocks = f"{self._updates_count} block{'s' if self._updates_count > 1 else ''}"
        Console.info(
            "Structure differs by {difference} from last generation.",
            difference=f"{percentage:.1f}%"
            if percentage >= 0.1
            else f"{blocks} (< 0.1%)",
        )


def _get_cache_file(world_path: Path) -> Path:
    file_name = hashlib.sha256(str(world_path).encode()).hexdigest()[:24]
    cache_dir = Path(user_cache_dir(APP_NAME))
    return cache_dir / file_name


def _load_cache(world_path: Path) -> CacheData | None:
    cache_file = _get_cache_file(world_path)
    # validate cache
    if not (world_path / cache_file.name).exists():
        cache_file.unlink(missing_ok=True)
        return None

    try:
        with cache_file.open("rb") as f:
            return msgpack.decode(f.read(), type=CacheData)
    except Exception:
        return None


def _save_cache(world_path: Path, cache: CacheData) -> None:
    cache_file = _get_cache_file(world_path)
    with (world_path / cache_file.name).open("w") as f:
        f.write(APP_NAME)  # marker file to validate cache next time

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with cache_file.open("wb") as f:
        f.write(msgpack.encode(cache))
