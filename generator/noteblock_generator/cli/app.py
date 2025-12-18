from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from typer import Context, Option, Typer

from .. import __version__
from ..core.coordinates import XYZ
from ..data import loader, watcher
from ..data.schema import BlockState
from .args import Align, Dimension, Facing, Tilt, Walkable


def _show_version(ctx: Context, value: bool):
    if value:
        print(__version__)
        ctx.exit()


def _show_help(ctx: Context, value: bool):
    if value:
        typer.echo(ctx.get_help())
        ctx.exit()


app = Typer(add_completion=False)


@app.command(no_args_is_help=True)
def _(
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
            help="Watch input and regenerate on changes",
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
        # must be list for typer's help message
    ] = ["stone"],  # pyright: ignore[reportCallInDefaultInitializer]
    walkable: Annotated[
        Walkable,
        Option(
            help="Ensure player can walk on top of the structure",
            rich_help_panel="Customization",
        ),
    ] = Walkable.partial,
    preserve_terrain: Annotated[
        bool,
        Option(
            "--preserve-terrain",
            help="Preserve existing blocks wherever possible",
            show_default="clear the area",
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
        Align,
        Option(
            "--align",
            help="Direction for the structure's width",
            rich_help_panel="Positioning",
        ),
    ] = Align.center,
    _version: Annotated[
        bool,
        Option("--version", is_eager=True, hidden=True, callback=_show_version),
    ] = False,
    _help: Annotated[
        bool,
        Option("--help", is_eager=True, hidden=True, callback=_show_help),
    ] = False,
):
    from ..core.generator import Generator
    from ..core.session import GeneratingSession

    generator = Generator(
        session=GeneratingSession(world_path),
        coordinates=coordinates,
        dimension=dimension,
        facing=facing,
        tilt=tilt,
        align=align,
        theme=theme,
        walkable=walkable,
        preserve_terrain=preserve_terrain,
    )

    if not watch:
        data = loader.load(input_path)
        generator.generate(data)
        return

    for data in watcher.watch(input_path):
        generator.generate(data, cached=True)
