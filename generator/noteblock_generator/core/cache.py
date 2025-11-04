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
        serialized = msgpack.encode(
            {k: str(v) for k, v in kwargs.items()}, order="deterministic"
        )
        return hashlib.sha256(serialized).hexdigest()

    @staticmethod
    def delete(world_path: Path) -> None:
        _get_cache_file(world_path).unlink(missing_ok=True)
        _delete_key(world_path)

    def __init__(self, world_path: Path, key: str):
        self._world_path = world_path
        self._key = key
        self._cached_length = 0
        self._data: CacheData | None = None

    def has_data(self):
        return bool(self._cached_length)

    def update(self, *, blocks: BlockMap):
        if not self._data:
            return

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

    def __enter__(self):
        if cache := _load_cache(self._world_path, self._key):
            self._data = cache
            self._cached_length = len(self._data.blocks)
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

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self._data:
            return

        if not exc_type:
            self._data.last_modified = datetime.now().timestamp()
            _save_cache(self._world_path, self._key, self._data)


def _calculate_difference(blocks: BlockMap, cached_blocks: BlockMap) -> BlockMap:
    return {
        k: v
        for k, v in blocks.items()
        if k not in cached_blocks or cached_blocks[k] != v
    }


_CACHE_DIR = Path(user_cache_dir(APP_NAME))


def _get_cache_file(world_path: Path) -> Path:
    return _CACHE_DIR / Cache.get_key(world_path=world_path)


def _load_cache(world_path: Path, key: str) -> CacheData | None:
    if not _validate_key(world_path, key):
        return None

    try:
        with _get_cache_file(world_path).open("rb") as f:
            return msgpack.decode(f.read(), type=CacheData)
    except FileNotFoundError:
        pass


def _save_cache(world_path: Path, key: str, data: CacheData) -> None:
    cache_file = _get_cache_file(world_path)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with cache_file.open("wb") as f:
        f.write(msgpack.encode(data))
    _create_key(world_path, key)


def _create_key(world_path: Path, key: str):
    with (world_path / f"{APP_NAME}.cache").open("w") as f:
        f.write(key)


def _validate_key(world_path: Path, key: str) -> bool:
    try:
        with (world_path / f"{APP_NAME}.cache").open("r") as f:
            return f.read() == key
    except FileNotFoundError:
        return False


def _delete_key(world_path: Path) -> None:
    try:
        (world_path / f"{APP_NAME}.cache").unlink()
    except FileNotFoundError:
        pass
