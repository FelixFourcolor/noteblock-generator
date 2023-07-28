#!/usr/bin/env python
import json
import logging
import shutil
import sys
from pathlib import Path


def _main(_in: str | Path, _out: str | Path = None):
    from generator import generate
    from translator import Composition

    with open((_in := Path(_in)), "r") as f:
        composition = Composition(**json.load(f))
    if _out is None:
        _out = _in.parent / str(composition)
    try:
        shutil.copytree(Path(sys.path[0]) / "New World", _out)
    except FileExistsError:
        pass
    generate(composition, _out)


def main():
    logging.basicConfig(level=logging.WARNING)
    _main(*sys.argv[1:])


if __name__ == "__main__":
    main()
