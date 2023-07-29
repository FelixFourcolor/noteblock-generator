#!/usr/bin/env python
import json
import logging
import sys
from pathlib import Path


def _main(_in: str | Path, _out: str | Path, *location_args: str):
    from generator import generate
    from translator import Composition

    with open((_in := Path(_in)), "r") as f:
        composition = Composition(**json.load(f))
    location = tuple(map(int, location_args))
    generate(composition, _out, location)


def main():
    logging.basicConfig(level=logging.WARNING)
    _main(*sys.argv[1:])


if __name__ == "__main__":
    main()
