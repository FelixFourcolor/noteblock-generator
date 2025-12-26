from __future__ import annotations

import contextlib
import secrets
import shutil
import tempfile
import time
import zlib
from pathlib import Path

from .. import APP_NAME


def backup_files(src: Path, patience: int = 3):
    class PermissionDenied(Exception): ...

    def copyfile(src: str, dst: str):
        try:
            return shutil.copy2(src, dst)
        except PermissionError as e:
            # windows locks this file, but no need to copy it, so just ignore
            if Path(src).name != "session.lock":
                # PermissionError raised here will be
                # propagated by shutil.copytree as OSError, which is not helpful.
                # So raise this custom exception instead.
                raise PermissionDenied(f"{src}: {e}")

    def copy(src: str, dst: str):
        src_path = Path(src)
        if src_path.is_dir():
            shutil.copytree(src, dst, copy_function=copyfile)
        elif src_path.is_file():
            copyfile(src, dst)

    temp_dir = Path(tempfile.gettempdir()) / APP_NAME
    temp_dir.mkdir(exist_ok=True)

    name = Path(src).name
    for _ in range(patience):
        try:
            copy(str(src), str(dst := temp_dir / name))
        except FileExistsError:
            name += f"_{secrets.token_hex(3)}"
        except PermissionDenied as e:
            raise PermissionError(e)
        else:
            return str(dst)


def hash_files(src: Path, *, patience=2) -> int | None:
    deadline = time.monotonic() + patience

    def check_time():
        if time.monotonic() >= deadline:
            raise TimeoutError

    def update(src: Path, hash: int) -> int:
        if src.is_file():
            return update_file(src, hash)
        if src.is_dir():
            return update_dir(src, hash)
        return hash

    READ_CHUNK = 64 * 1024  # 64 KB

    def update_file(src: Path, hash: int) -> int:
        with src.open("rb") as f:
            for chunk in iter(lambda: f.read(READ_CHUNK), b""):
                check_time()
                hash = zlib.crc32(chunk, hash)

        return hash

    def update_dir(src: Path, hash: int) -> int:
        for path in sorted(src.iterdir(), key=lambda p: str(p)):
            check_time()
            hash = zlib.crc32(path.name.encode(), hash)
            hash = update(path, hash)
        return hash

    with contextlib.suppress(PermissionError):
        if not src.exists():
            raise FileNotFoundError()
        try:
            return update(src, 0)
        except TimeoutError:
            return None
