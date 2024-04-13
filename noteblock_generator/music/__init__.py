import pickle
import zlib
from pathlib import Path

from platformdirs import user_cache_dir

from . import compiler, loader, parser


def compile(src: str):  # noqa: A001
    src_code = loader.load(src)  # TODO: error handling

    cache = _Cache(src_code)
    if (out := cache.get()) is not None:
        return out

    out = compiler.compile(parser.parse(src_code))  # TODO: error handling
    cache.save(out)
    return out


_cache_dir = Path(user_cache_dir("noteblock-generator", ensure_exists=True))


class _Cache:
    def __init__(self, src_code: str):
        # TODO: I have no idea what to do with hash collisions, let's just hope it won't happen.
        hash_src = zlib.crc32(src_code.encode())
        self._file = _cache_dir / str(hash_src)

    def get(self) -> compiler.T_Data | None:
        try:
            cached_result = self._file.read_bytes()
        except FileNotFoundError:
            pass
        else:
            return pickle.loads(cached_result)

    def save(self, data: compiler.T_Data):
        with self._file.open("wb") as f:
            pickle.dump(data, f)
