import logging
import os
import sys
from argparse import ArgumentParser
from typing import NamedTuple

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(message)s")


_HOME = os.path.expanduser("~")


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


class UserError(Exception):
    pass


def get_args():
    parser = ArgumentParser()
    parser.add_argument("music_source", help="path to music source")
    parser.add_argument(
        "world_path", help="path to Minecraft world (Java Edition only)"
    )
    parser.add_argument(
        "--location",
        nargs="*",
        default=["~", "~", "~"],
        help="build location (in '<x> <y> <z>'); default is player's location",
    )
    parser.add_argument(
        "--dimension",
        default=None,
        help="build dimension; default is player's dimension",
    )
    parser.add_argument(
        "--orientation",
        nargs="*",
        default=["~", "~"],
        help="build orientation (in '<horizontal> <vertical>'); default is player's orientation",
    )
    parser.add_argument(
        "--theme",
        default="stone",
        help="redstone-conductive block; default is stone",
    )
    parser.add_argument(
        "--blend",
        action="store_true",
        help="blend the structure with its environment",
    )
    log_level = parser.add_mutually_exclusive_group()
    log_level.add_argument(
        "--verbose", action="store_true", help="increase output verbosity"
    )
    log_level.add_argument(
        "--quiet",
        action="store_true",
        help="decrease output verbosity",
    )
    return parser.parse_args(None if sys.argv[1:] else ["-h"])


def parse_args():
    args = get_args()

    # location
    if len(args.location) != 3:
        raise UserError("Location requires 3 values")
    location = Location(*map(Coordinate, args.location))

    # dimension
    if (dimension := args.dimension) is not None:
        valid_choices = ("overworld", "the_nether", "the_end")
        dimension = dimension.lower().strip()
        if dimension not in valid_choices:
            raise UserError(f"Invalid dimension; expected one of {valid_choices}")

    # orientation
    if len(args.orientation) != 2:
        raise UserError("Orientation requires 2 values")
    orientation = Orientation(*map(Coordinate, args.orientation))

    # verbosity
    if args.quiet:
        logger.setLevel(logging.WARNING)
    elif args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # parse Composition last, because it takes the most time,
    # so that we catch command-line errors quickly

    from .parser import parse

    composition = parse(args.music_source)

    return {
        "world_path": args.world_path,
        "composition": composition,
        "location": location,
        "dimension": dimension,
        "orientation": orientation,
        "theme": args.theme,
        "blend": args.blend,
    }
