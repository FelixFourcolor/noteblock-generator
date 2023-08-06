import sys
from argparse import ArgumentParser
from typing import NamedTuple

from noteblock_generator.compiler import Composition, UserError


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


def get_args():
    parser = ArgumentParser(
        description="Generate music compositions in Minecraft noteblocks.",
    )
    parser.add_argument("path_in", help="path to music json file")
    parser.add_argument("path_out", help="path to Minecraft world")
    parser.add_argument(
        "-l",
        "--location",
        nargs="*",
        default=["~", "~", "~"],
        help="build location (in x y z); default is ~ ~ ~",
    )
    parser.add_argument(
        "-o",
        "--orientation",
        nargs="*",
        default=["+", "+", "+"],
        help=("build orientation (in x y z); default is + + +"),
    )
    parser.add_argument(
        "-b",
        "--block",
        default="stone",
        help="opaque block for redstone components; default is stone",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help=(
            "clear the space before generating; "
            "required in order to generate in a non-empty world, "
            "but will take more time"
        ),
    )
    return parser.parse_args(None if sys.argv[1:] else ["-h"])


def parse_args():
    args = get_args()

    if len(args.location) != 3:
        raise UserError("3 coordinates are required.")
    location: list[Coordinate] = []
    for arg in args.location:
        if relative := arg.startswith("~"):
            arg = arg[1:]
        if not arg:
            value = 0
        else:
            try:
                value = int(arg)
            except ValueError:
                raise UserError(f"Expected integer coordinates; found {arg}.")
        location.append(Coordinate(value, relative=relative))

    if len(args.orientation) != 3:
        raise UserError("3 orientations are required.")
    orientation: list[bool] = []
    _options = "+-"
    for arg in args.orientation:
        try:
            orientation.append(_options.index(arg) == 0)
        except ValueError:
            raise UserError(f"{arg} is not a valid direction; expected + or -.")

    return args.path_out, {
        "composition": Composition.compile(args.path_in),
        "location": Location(*location),
        "orientation": Orientation(*orientation),
        "block": args.block,
        "clear": args.clear,
    }


def main():
    try:
        path_out, kwargs = parse_args()
    except UserError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    from noteblock_generator.generator import World

    with World(path_out) as world:
        world.generate(**kwargs)


if __name__ == "__main__":
    main()
