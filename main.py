#!/usr/bin/env python
import json
import logging
import shutil
import sys
from pathlib import Path


def generate(path_in: str | Path, path_out: str | Path = None):
    from generator import generate
    from music import Composition

    path_in = Path(path_in)
    with open(path_in, "r") as f:
        kwargs = json.load(f)

    composition = Composition(**kwargs)

    if path_out is None:
        path_out = path_in.parent / str(composition)
    shutil.copytree(Path(sys.path[0]) / "New World", path_out, dirs_exist_ok=True)

    generate(composition, path_out)


def main():
    logging.basicConfig(level=logging.WARNING)
    generate(*sys.argv[1:])


if __name__ == "__main__":
    main()
