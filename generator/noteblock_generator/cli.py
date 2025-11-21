from __future__ import annotations

import logging
import os
import time
from enum import Enum
from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING, Annotated

import typer
import watchfiles
from click import UsageError
from typer import Context, Option, Typer

from noteblock_generator import VERSION

from .core.api.loader import load
from .core.api.types import BlockState
from .core.coordinates import XYZ
from .core.generator import Generator

if TYPE_CHECKING:
    from collections.abc import Callable

logging.disable()  # disable amulet's logging


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


def _show_version(ctx: Context, value: bool):
    if value:
        print(VERSION)
        ctx.exit()


def _show_help(ctx: Context, value: bool):
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
            rich_help_panel="Input & output",
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
            help="Input data (noteblock compiler's output)",
            show_default="read from stdin",
            metavar="file",
            rich_help_panel="Input & output",
            exists=True,
            file_okay=True,
            dir_okay=False,
        ),
    ] = None,
    watch: Annotated[
        bool,
        Option(
            "--watch",
            help="Watch input file and regenerate on changes",
            rich_help_panel="Input & output",
        ),
    ] = False,
    theme: Annotated[
        list[BlockState],
        Option(
            "--theme",
            "-t",
            help="Building block; must be redstone-conductive",
            rich_help_panel="Customization",
            metavar="name",
        ),
    ] = ["stone"],  # pyright: ignore[reportCallInDefaultInitializer] # must be list for typer's help message
    blend: Annotated[
        bool,
        Option(
            "--blend",
            help="Preserve existing world blocks where possible",
            show_default="preemptively clear entire area",
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
            help="Direction for the structure's width",
            rich_help_panel="Positioning",
        ),
    ] = Alignment.center,
    _version: Annotated[
        bool,
        Option("--version", is_eager=True, hidden=True, callback=_show_version),
    ] = False,
    _help: Annotated[
        bool,
        Option("--help", is_eager=True, hidden=True, callback=_show_help),
    ] = False,
):
    generator = Generator(
        world_path=world_path,
        coordinates=coordinates,
        dimension=dimension.name if dimension else None,
        facing=facing.name if facing else None,
        tilt=tilt.name if tilt else None,
        align=align.name,
        theme=theme,
        blend=blend,
    )

    if not watch:
        generator.generate(data=load(input_path), cache=False)
        return

    if not input_path:
        raise UsageError("--watch requires an input file.")

    # Artificially triggers a file change to get watchfiles started.
    # Alternative would be to call another generate() before the watch loop;
    # but then changes during the initial run would be missed.
    def trigger_initial_run():
        time.sleep(0.2)
        os.utime(input_path)

    trigger_thread = Thread(target=trigger_initial_run, daemon=True)
    trigger_thread.start()

    is_first_call = True
    for _ in watchfiles.watch(input_path, debounce=0, rust_timeout=0):
        try:
            data = load(input_path)
        except UsageError as e:
            if is_first_call:
                raise e
        else:
            # nbc's protocol: clearing the input file is the signal to recompile
            input_path.write_bytes(b"")
            generator.generate(data, cache=True)
            is_first_call = False
