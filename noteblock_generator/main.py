import logging
import sys
from argparse import ArgumentParser
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
        help="build location (in x y z); default is player's location",
    )
    parser.add_argument(
        "--dimension",
        default=None,
        help="build dimension; default is player's dimension",
    )
    parser.add_argument(
        "--orientation",
        nargs="*",
        default=None,
        help=(
            "build orientation (in horizontal, vertical); default is player's orientation"
        ),
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
                raise UserError(f"Expected integer coordinates; received {arg}")
        _location.append(Coordinate(value, relative=relative))
    location = Location(*_location)

    # dimension
    if (dimension := args.dimension) is not None:
        if not dimension.startswith("minecraft:"):
            dimension = "minecraft:" + dimension

    # orientation
    if (orientation := args.orientation) is not None:
        if len(args.orientation) != 2:
            raise UserError("Orientation requires 2 values")
        for index, value in enumerate(orientation):
            try:
                orientation[index] = float(value)
            except ValueError:
                raise UserError(
                    f"Expected float values for orientation; received {value}"
                )
        if not (-180 <= orientation[0] <= 180):
            raise UserError("Horizontal orientation must between -180 and 180")
        if not (-90 <= orientation[1] <= 90):
            raise UserError("Vertical orientation must between -90 and 90")

    # parse music
    from .parser import parse

    composition = parse(args.music_source)

    # load world
    from .world import World

    world = World(args.minecraft_world)

    # return
    return {
        "world": world,
        "composition": composition,
        "location": location,
        "dimension": dimension,
        "orientation": orientation,
        "theme": args.theme,
        "blend": args.blend,
        "no_confirm": args.no_confirm,
    }


def main():
    try:
        args = parse_args()
        from .generator import Generator

        Generator(**args)()
    except UserError as e:
        logger.error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
