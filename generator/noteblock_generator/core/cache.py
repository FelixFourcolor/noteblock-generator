import hashlib
from datetime import datetime
from pathlib import Path
from typing import final

from humanize import naturaltime
from msgspec import Struct, msgpack
from platformdirs import user_cache_dir

from noteblock_generator import APP_NAME

from ..api.types import BlockMap
from .utils.console import Console


class CacheData(Struct):
    last_modified: float = datetime.now().timestamp()
    blocks: BlockMap = {}


_CACHE_MISS = object()


@final
class Cache:
    @staticmethod
    def get_key(**kwargs) -> str:
        serialized = msgpack.encode(kwargs, order="deterministic")
        return hashlib.sha256(serialized).hexdigest()

    @staticmethod
    def delete(key: str) -> None:
        _get_cache_file(key).unlink(missing_ok=True)

    def __init__(self, key: str):
        self._path = _get_cache_file(key)
        if cache := _load_cache(self._path):
            self._data = cache
            Console.info(
                "Using previous generation from {whence}",
                whence=naturaltime(
                    datetime.now() - datetime.fromtimestamp(cache.last_modified)
                ),
            )
        else:
            self._data = CacheData()
            Console.warn(
                "No previous generation found. This run will generate from scratch."
            )
        self._cached_length = len(self._data.blocks)

    def has_data(self):
        return bool(self._cached_length)

    def update(self, *, blocks: BlockMap):
        updated_blocks = _calculate_difference(blocks, self._data.blocks)
        self._data.blocks |= blocks

        if not updated_blocks:
            Console.success("Structure unchanged; nothing to generate.")
        elif self._cached_length:
            percentage = (len(updated_blocks) / (self._cached_length)) * 100
            Console.info(
                "Structure differs by {difference} from last generation.",
                difference=f"{percentage:.1f}%" if percentage >= 0.1 else "< 0.1%",
            )

        return updated_blocks

    def save(self):
        self._data.last_modified = datetime.now().timestamp()
        _save_cache(self._path, self._data)


def _calculate_difference(blocks: BlockMap, cached_blocks: BlockMap) -> BlockMap:
    return {
        k: v
        for k, v in blocks.items()
        if k not in cached_blocks or cached_blocks[k] != v
    }


def _get_cache_file(key: str) -> Path:
    cache_dir = Path(user_cache_dir(APP_NAME))
    return cache_dir / key


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
