import logging
import sys
from argparse import ArgumentParser
from functools import partial
from typing import NamedTuple

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format="%(levelname)s - %(message)s")


class Coordinate(int):
    relative: bool

    def __new__(cls, value: int, relative=False):
        self = super().__new__(cls, value)
        self.relative = relative
        return self


class Location(NamedTuple):
    x: Coordinate
    y: Coordinate
    z: Coordinate


class Orientation(NamedTuple):
    x: bool
    y: bool
    z: bool


class UserError(Exception):
    pass


def get_args():
    parser = ArgumentParser()
    parser.add_argument("music_source", help="path to music source")
    parser.add_argument("minecraft_world", help="path to Minecraft world")
    parser.add_argument(
        "--location",
        nargs="*",
        default=["~", "~", "~"],
        help="build location (in x y z); default is ~ ~ ~",
    )
    parser.add_argument(
        "--dimension",
        default=None,
        help="build dimension; default is player's dimension",
    )
    parser.add_argument(
        "--orientation",
        nargs="*",
        default=["+", "+", "+"],
        help=("build orientation (in x y z); default is + + +"),
    )
    parser.add_argument(
        "--theme",
        default="stone",
        help="opaque block for redstone components; default is stone",
    )
    parser.add_argument(
        "--blend",
        action="store_true",
        help=("blend the structure in with its environment (EXPERIMENTAL)"),
    )
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        help=("skip user confirmation"),
    )
    return parser.parse_args(None if sys.argv[1:] else ["-h"])


def parse_args():
    args = get_args()

    # location
    if len(args.location) != 3:
        raise UserError("3 coordinates are required")
    _location: list[Coordinate] = []
    for arg in args.location:
        if relative := arg.startswith("~"):
            arg = arg[1:]
        if not arg:
            value = 0
        else:
            try:
                value = int(arg)
            except ValueError:
                raise UserError(f"Expected integer coordinates; found {arg}")
        _location.append(Coordinate(value, relative=relative))
    location = Location(*_location)

    # dimension
    if (dimension := args.dimension) is not None:
        if not dimension.startswith("minecraft:"):
            dimension = "minecraft:" + dimension

    # orientation
    if len(args.orientation) != 3:
        raise UserError("3 orientations are required")
    _orientation: list[bool] = []
    _options = "+-"
    for arg in args.orientation:
        try:
            _orientation.append(_options.index(arg) == 0)
        except ValueError:
            raise UserError(f"{arg} is not a valid direction; expected + or -")
    orientation = Orientation(*_orientation)

    # parse music
    from .parser import parse

    composition = parse(args.music_source)

    # load world
    from .generator import World

    world = World(args.minecraft_world)
    return partial(
        world.generate,
        composition=composition,
        location=location,
        dimension=dimension,
        orientation=orientation,
        theme=args.theme,
        blend=args.blend,
        no_confirm=args.no_confirm,
    )


def main():
    try:
        generator = parse_args()
        generator()
    except UserError as e:
        logger.error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
