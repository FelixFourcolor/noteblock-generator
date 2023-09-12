import sys
from argparse import ArgumentParser
from typing import NamedTuple

from .compiler import Composition, UserError, logger


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
        "--clear",
        action="store_true",
        help=("clear the space before generating"),
    )
    return parser.parse_args(None if sys.argv[1:] else ["-h"])


def parse_args():
    args = get_args()

    # path in
    composition = Composition.compile(args.path_in)

    # path out
    path_out = args.path_out

    # location
    if len(args.location) != 3:
        raise UserError("3 coordinates are required.")
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
                raise UserError(f"Expected integer coordinates; found {arg}.")
        _location.append(Coordinate(value, relative=relative))
    location = Location(*_location)

    # dimension
    choices = ["overworld", "the_nether", "the_end"]
    if (dimension := args.dimension) is not None:
        if dimension not in choices:
            raise UserError(
                f"{dimension} is not a valid dimension; expected one of {choices}."
            )
        dimension = "minecraft:" + dimension

    # orientation
    if len(args.orientation) != 3:
        raise UserError("3 orientations are required.")
    _orientation: list[bool] = []
    _options = "+-"
    for arg in args.orientation:
        try:
            _orientation.append(_options.index(arg) == 0)
        except ValueError:
            raise UserError(f"{arg} is not a valid direction; expected + or -.")
    orientation = Orientation(*_orientation)

    # theme
    theme = args.theme

    # clear
    clear = args.clear

    return {
        "composition": composition,
        "location": location,
        "dimension": dimension,
        "orientation": orientation,
        "theme": theme,
        "clear": clear,
        "path_out": path_out,
    }


def main():
    logger.info("Compiling...")
    try:
        kwargs = parse_args()
    except UserError as e:
        logger.error(e)
        sys.exit(1)

    from .generator import generate

    logger.info("Generating... This may take a while. Do not enter the world yet.")
    generate(**kwargs)
    logger.info("All done!")


if __name__ == "__main__":
    main()
