#!/usr/bin/env python
import json
import logging
import sys


def generate(path_in: str, path_out: str):
    from minecraft import generate
    from music import Composition

    with open(path_in, "r") as f:
        kwargs = json.load(f)

    composition = Composition(**kwargs)
    generate(composition, path_out)


def main():
    logging.basicConfig(level=logging.WARNING)
    generate(path_in=sys.argv[1], path_out=sys.argv[2])


if __name__ == "__main__":
    main()
