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
                raise UserError(f"Expected integer values; received {_value}")
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
  -l, --location X Y Z                  build location; default is player's location
  -d, --dimension DIMENSION             build dimension; default is player's dimension
  -o, --orientation HORIZONTAL VERTICAL build orientation; default is player's orientation
  -t, --theme THEME                     redstone-conductive block; default is stone
  --blend                               blend the structure with its environment

output options:
  -q, --quiet                           decrease output verbosity; can be used up to 3 times
  --debug                               show full exception traceback if an error occurs

help:
  -h, --help                            show this help message and exit
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
    parser.add_argument("-d", "--dimension", default=None)
    parser.add_argument(
        "-o", "--orientation", action="store", nargs=2, default=["~", "~"]
    )
    parser.add_argument("-t", "--theme", default="stone")
    parser.add_argument("--blend", action="store_true")
    parser.add_argument("-q", "--quiet", action="count", default=0)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args(None if sys.argv[1:] else ["-h"])


_error_logger = logger.getChild("")
_error_logger.setLevel(logging.CRITICAL)


def parse_args():
    args = get_args()

    # location
    location = Location(*map(Coordinate, args.location))

    # dimension
    if (dimension := args.dimension) is not None:
        valid_choices = ("overworld", "the_nether", "the_end")
        dimension = dimension.lower().strip()
        if dimension not in valid_choices:
            raise UserError(f"Invalid dimension; expected one of {valid_choices}")

    # orientation
    orientation = Orientation(*map(Coordinate, args.orientation))

    # verbosity
    match args.quiet:
        case 3:
            logger.setLevel(logging.CRITICAL)
        case 2:
            logger.setLevel(logging.WARNING)
        case 1:
            logger.setLevel(logging.INFO)
        case _:
            logger.setLevel(logging.DEBUG)
    if args.debug:
        _error_logger.setLevel(logging.DEBUG)

    # parse Composition and load Generator last,
    # because because they take the most time,
    # so that we catch command-line errors quickly

    from .parser import Composition

    composition = Composition(getattr(args, "path/to/music/source"))

    # Load Generator after, so that we catch writing errors quickly

    from .generator import Generator

    return Generator(
        world_path=getattr(args, "path/to/minecraft/world"),
        composition=composition,
        location=location,
        dimension=dimension,
        orientation=orientation,
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
        dev_error = False
        logger.error(format_error(e))
        if not isinstance(e, UserError):
            dev_error = True
            _error_logger.debug("".join(traceback.format_exception(e)))
        while (e := e.__cause__) is not None:
            logger.info(format_error(e))
            if not isinstance(e, UserError):
                dev_error = True
                _error_logger.debug("".join(traceback.format_exception(e)))
        if dev_error:
            logger.debug(
                "\033[33m"
                "If you could kindly report this error, I'd appreciate it. -- Felix"
                "\033[m"
            )
        sys.exit(1)
