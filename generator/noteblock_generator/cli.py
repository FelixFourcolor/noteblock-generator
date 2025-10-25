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


class Facing(Enum):
    north = "-z"
    south = "+z"
    east = "+x"
    west = "-x"


class Tilt(Enum):
    up = "up"
    down = "down"


class Alignment(Enum):
    left = "left"
    center = "center"
    right = "right"


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
            rich_help_panel="Input & Output",
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
            help="Compiled music source",
            show_default="read from stdin",
            metavar="file",
            rich_help_panel="Input & Output",
            exists=True,
            file_okay=True,
            dir_okay=False,
        ),
    ] = None,
    theme: Annotated[
        str,
        Option(
            "--theme",
            help="Primary building block; must be redstone-conductive",
            rich_help_panel="Customization",
            metavar="block_name",
        ),
    ] = "stone",
    blend: Annotated[
        bool,
        Option(
            "--blend/--clear",
            help="Preserve existing world blocks for a more natural look",
            rich_help_panel="Customization",
        ),
    ] = False,
    coordinates: Annotated[
        XYZ | None,
        Option(
            "--at",
            help="Coordinates to place the structure",
            show_default="player's coordinates",
            rich_help_panel="Positioning",
            metavar="<X Y Z>",
        ),
    ] = None,
    dimension: Annotated[
        Dimension | None,
        Option(
            "--dim",
            help="Dimension to place the structure in",
            show_default="player's dimension",
            rich_help_panel="Positioning",
            case_sensitive=False,
        ),
    ] = None,
    facing: Annotated[
        Facing | None,
        Option(
            "--face",
            help="Direction for the structure's length",
            show_default="player's look direction",
            rich_help_panel="Positioning",
            case_sensitive=False,
            metavar="[-X|+X|-Z|+Z]",
        ),
    ] = None,
    tilt: Annotated[
        Tilt | None,
        Option(
            "--tilt",
            help="Direction for the structure's height",
            show_default="player's look direction",
            rich_help_panel="Positioning",
        ),
    ] = None,
    align: Annotated[
        Alignment,
        Option(
            "--align",
            help="Alignment for the structure's width",
            rich_help_panel="Positioning",
        ),
    ] = Alignment.center,
    partial: Annotated[
        bool,
        Option(
            "--partial/--full",
            help="Generate only changed blocks since last run",
            rich_help_panel="Advanced",
        ),
    ] = False,
    _: Annotated[  # to hide --help in the help message
        bool,
        Option(
            "--help",
            "-h",
            is_eager=True,
            hidden=True,
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
        coordinates=coordinates,
        dimension=dimension.name if dimension else None,
        facing=facing.name if facing else None,
        tilt=tilt.name if tilt else None,
        align=align.name,
        theme=theme,
        blend=blend,
        partial=partial,
    )
