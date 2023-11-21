import logging
import os
import sys
import traceback
from argparse import ArgumentParser
from typing import NamedTuple

import colorama

colorama.just_fix_windows_console()

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(message)s")


_HOME = os.path.expanduser("~")  # noqa: PTH111


class Coordinate(int):
    relative: bool

    def __new__(cls, _value: str, /):
        if not (relative := _value != (_value := _value.removeprefix("~"))):
            relative = _value != (_value := _value.removeprefix(_HOME))
        if not _value:
            value = 0
        else:
            try:
                value = int(_value)
            except ValueError:
                raise ValueError(_value)
        self = super().__new__(cls, value)
        self.relative = relative
        return self


class Location(NamedTuple):
    x: Coordinate
    y: Coordinate
    z: Coordinate


class Orientation(NamedTuple):
    horizontal: Coordinate
    vertical: Coordinate


class Error(Exception):
    pass


class DeveloperError(Error):
    pass


class UserError(Error):
    pass


class Parser(ArgumentParser):
    def format_help(self):
        return """usage: noteblock-generator path/to/music/source path/to/minecraft/world [--OPTIONS]

build options:
  -l/--location X Y Z                  build location; default is player's location
  -d/--dimension DIMENSION             build dimension; default is player's dimension
  -o/--orientation HORIZONTAL VERTICAL build orientation; default is player's orientation
  -t/--theme BLOCK                     redstone-conductive block; default is stone
  --blend                              blend the structure with its environment

output options:
  -q/--quiet                           decrease output verbosity; can be used up to 3 times
  --debug                              show full exception traceback if an error occurs

help:
  -h/--help                            show this help message and exit
"""  # noqa: E501

    def error(self, message):
        self.print_help()
        raise UserError(message)


def get_args():
    parser = Parser()
    parser.add_argument("path/to/music/source")
    parser.add_argument("path/to/minecraft/world")
    parser.add_argument(
        "-l", "--location", action="store", nargs=3, default=["~", "~", "~"]
    )
    parser.add_argument(
        "-o", "--orientation", action="store", nargs=2, default=["~", "~"]
    )
    parser.add_argument(
        "-d",
        "--dimension",
        choices=("overworld", "the_nether", "the_end"),
        default=None,
    )
    parser.add_argument("-t", "--theme", default="stone")
    parser.add_argument("--blend", action="store_true")
    parser.add_argument("-q", "--quiet", action="count", default=0)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


_error_logger = logger.getChild("")
_error_logger.setLevel(logging.CRITICAL)


def parse_args():
    # parse cli arguments
    args = get_args()

    # verbosity
    match args.quiet:
        case 0:
            logger.setLevel(logging.DEBUG)
        case 1:
            logger.setLevel(logging.INFO)
        case 2:
            logger.setLevel(logging.WARNING)
        case _:
            logger.setLevel(logging.CRITICAL)
    if args.debug:
        _error_logger.setLevel(logging.DEBUG)

    # location
    try:
        location = Location(*map(Coordinate, args.location))
    except ValueError as e:
        raise UserError(f"argument -l/--location: invalid int value: {e}")

    # orientation
    try:
        orientation = Orientation(*map(Coordinate, args.orientation))
    except ValueError as e:
        raise UserError(f"argument -o/--orientation: invalid int value: {e}")

    # parse Composition and load Generator last so that we catch cli errors quickly

    from .parser import Composition

    composition = Composition(getattr(args, "path/to/music/source"))

    # Load Generator after, so that we catch writing errors quickly

    from .generator import Generator

    return Generator(
        world_path=getattr(args, "path/to/minecraft/world"),
        composition=composition,
        location=location,
        orientation=orientation,
        dimension=args.dimension,
        theme=args.theme,
        blend=args.blend,
    )


def format_error(e: BaseException):
    return (
        "\033[31;1m"  # red, bold
        + ("ERROR" if isinstance(e, UserError) else type(e).__name__)  # error type
        + "\033[22m"  # stop bold
        + f": {e}"  # error message
        + "\033[m"  # stop red
    )


def main():
    try:
        generator = parse_args()
        generator()
    except Exception as e:
        dev_error = not isinstance(e, UserError)
        logger.error(format_error(e))
        _error_logger.debug("".join(traceback.format_exception(e)))
        while (e := e.__cause__) is not None:
            logger.info(format_error(e))
            _error_logger.debug("".join(traceback.format_exception(e)))
        if dev_error:
            logger.debug(
                "\033[33m"
                "If you could kindly report this error, I would appreciate it. -- Felix"
                "\033[m"
            )
        sys.exit(1)
