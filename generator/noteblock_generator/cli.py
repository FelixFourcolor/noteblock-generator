import logging
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from click import UsageError
from typer import CallbackParam, Context, Option, Typer

from .api.loader import load_and_validate
from .core.coordinates import XYZ


class Dimension(Enum):
    overworld = "overworld"
    nether = "nether"
    the_end = "the_end"


class Direction(Enum):
    north = "-z"
    south = "+z"
    east = "+x"
    west = "-x"


class Tilt(Enum):
    up = "+y"
    down = "-y"


class Alignment(Enum):
    start = "start"
    center = "center"
    end = "end"


def help_callback(ctx: Context, _: CallbackParam, value: bool):
    if value:
        typer.echo(ctx.get_help())
        ctx.exit()


def __main(fn: Callable):
    app = Typer(add_completion=False)
    app.command(no_args_is_help=True)(fn)
    return app


@__main
def run(
    world_path: Annotated[
        Path,
        Option(
            "--out",
            "-o",
            help="Minecraft Java world save",
            show_default=False,
            metavar="directory",
            rich_help_panel="Paths",
            exists=True,
            file_okay=False,
            dir_okay=True,
            writable=True,
            resolve_path=True,
        ),
    ],
    input_path: Annotated[
        Path | None,
        Option(
            "--in",
            "-i",
            help="Compiled music source (noteblock-compiler's output)",
            show_default="read from stdin",
            metavar="file",
            rich_help_panel="Paths",
            exists=True,
            file_okay=True,
            dir_okay=False,
        ),
    ] = None,
    position: Annotated[
        XYZ | None,
        Option(
            "--at",
            help="Coordinates to place the structure",
            show_default="player's coordinates",
            rich_help_panel="Build location",
            metavar="<x y z>",
        ),
    ] = None,
    dimension: Annotated[
        Dimension | None,
        Option(
            "--dim",
            help="Dimension to place the structure in",
            show_default="player's dimension",
            rich_help_panel="Build location",
            case_sensitive=False,
        ),
    ] = None,
    direction: Annotated[
        Direction | None,
        Option(
            "--dir",
            help="Build direction (horizontal) starting from --at",
            show_default="player's look direction",
            rich_help_panel="Build location",
            case_sensitive=False,
        ),
    ] = None,
    tilt: Annotated[
        Tilt | None,
        Option(
            "--tilt",
            help="Build direction (vertical) starting from --at",
            show_default="player's look direction",
            rich_help_panel="Build location",
            case_sensitive=False,
        ),
    ] = None,
    theme: Annotated[
        str,
        Option(
            "--theme",
            "-t",
            help="Primary building block; must be redstone-conductive",
            rich_help_panel="Build customization",
            metavar="block name",
        ),
    ] = "stone",
    blend: Annotated[
        bool,
        Option(
            "--blend/--clear",
            help="Preserve surrounding blocks for a more natural look",
            rich_help_panel="Build customization",
        ),
    ] = False,
    walkable: Annotated[
        bool,
        Option(
            "--walkable/--unwalkable",
            help="Ensure the area above the structure is walkable",
            rich_help_panel="Build customization",
        ),
    ] = True,
    partial: Annotated[
        bool,
        Option(
            "--partial/--full",
            help="Generate only changed blocks since last run",
            rich_help_panel="Build customization",
        ),
    ] = False,
    _: Annotated[  # to hide --help in the help message
        bool,
        Option(
            "--help",
            hidden=True,
            is_eager=True,
            callback=help_callback,
        ),
    ] = False,
):
    try:
        data = load_and_validate(input_path)
    except Exception:
        raise UsageError("Invalid input data.")
    if not data:
        raise UsageError(
            "Missing input: Either provide file path with --in, or pipe content to stdin.",
        )

    logging.disable()  # disable amulet's logging
    from .core.generate import generate

    generate(
        data=data,
        world_path=world_path,
        position=position,
        dimension=dimension.value if dimension else None,
        direction=direction.name if direction else None,
        tilt=tilt.name if tilt else None,
        theme=theme,
        blend=blend,
        walkable=walkable,
        partial=partial,
    )
