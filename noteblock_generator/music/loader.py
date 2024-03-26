import json
import os
import re
from pathlib import Path

import yaml


def load(src_path: str):
    return _resolve_references(f'"file://{src_path}"', prefix=Path.cwd())  # TODO: error handling


def dereference(data: dict):
    return data.pop(_REF_KEYWORD)


_URI_PATTERN = re.compile(r'"file://([^"]+)"')
_REF_KEYWORD = "$ref"


def _resolve_references(source: str, *, prefix: Path) -> str:
    offset = 0
    for m in _URI_PATTERN.finditer(source):
        match, match_path = m.group(0, 1)
        path = _find_path(prefix / match_path)
        replacement = _load_reference(path)
        start = m.start() + offset
        end = m.end() + offset
        source = source[:start] + replacement + source[end:]
        offset += len(replacement) - len(match)
    return source


def _find_path(path: Path):
    def find(path: Path, /, *, match_name: str = None) -> Path | None:
        if path.is_dir():
            cwd, directories, files = next(os.walk(path))
            files = [f for f in files if f.endswith((".json", ".yaml"))]
            if len(files) == 1:
                return path / Path(files[0])
            for subpath in map(Path, files + directories):
                while (parent := path.parent) != path:
                    if found := find(cwd / subpath, match_name=path.stem):
                        return found
                    path = parent
                path = Path(cwd)
            return None
        if match_name is None or match_name == path.stem:
            return path

    if not path.exists():
        raise ValueError(f"{path} does not exist")
    if not (found := find(path)):
        raise ValueError(f"unrecognized music format for {path}")
    return found


def _load_reference(path: Path):
    text = _resolve_references(path.read_text(), prefix=path.parent)
    if isinstance(obj := yaml.safe_load(text), dict):
        obj["path"] = str(path)
    else:
        obj = {"path": str(path), _REF_KEYWORD: obj}
    return json.dumps(obj)  # we load yaml but dump json otherwise it doesn't work
