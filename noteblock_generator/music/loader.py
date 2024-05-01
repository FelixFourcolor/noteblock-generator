import json
import os
import re
from pathlib import Path

import yaml


def load(src_path: str) -> object:
    # TODO: error handling: path not found, or yaml syntax error
    path = _find_path(Path.cwd() / src_path)
    text = _resolve_references(path.read_text(), prefix=path.parent)
    if isinstance(raw_data := yaml.safe_load(text), dict):
        raw_data[PATH_KEY] = str(path)
    else:
        raw_data = {PATH_KEY: str(path), REF_KEY: raw_data}
    return raw_data


PATH_KEY = "$path"
REF_KEY = "$ref"
_REF_PATTERN = re.compile('["]?file://([^",\\n]+)["]?')


def _resolve_references(source: str, *, prefix: Path) -> str:
    def repl(reference: re.Match[str]) -> str:
        reference_path = reference.group(1)
        real_path = _find_path(prefix / reference_path)
        return _load_reference(real_path)

    return re.sub(_REF_PATTERN, repl, source)


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
    if isinstance(data := yaml.safe_load(text), dict):
        data[PATH_KEY] = str(path)
    else:
        data = {PATH_KEY: str(path), REF_KEY: data}
    # dump json instead of yaml, otherwise _resolve_references doesn't work
    return json.dumps(data)
