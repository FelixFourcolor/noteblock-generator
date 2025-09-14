from __future__ import annotations

from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING

from .chunks import ChunkProcessor
from .session import UserCancelled, WorldGeneratingSession
from .structure import Structure
from .utils.console import CancellableProgress, Console

if TYPE_CHECKING:
    from ..api.types import BuildingDTO
    from .coordinates import XYZ, DirectionName, TiltName


def generate(
    *,
    data: BuildingDTO,
    world_path: Path,
    theme: str,
    blend: bool,
    position: XYZ | None,
    dimension: str | None,
    direction: DirectionName | None,
    tilt: TiltName | None,
):
    with WorldGeneratingSession(world_path) as session:
        world = session.load_world()
        dimension = dimension or world.player_dimension

        structure = Structure(
            data=data,
            position=position or world.player_position,
            direction=direction or world.player_direction,
            tilt=tilt or world.player_tilt,
            theme=theme,
            blend=blend,
        )

        if blend:
            Console.warn(
                "Blend mode is experimental. Turn it off if you encounter issues."
            )

        bounds = structure.bounds
        Console.info(
            "The structure will occupy the space\n{start} to {end} in {dimension}.",
            start=(bounds.min_x, bounds.min_y, bounds.min_z),
            end=(bounds.max_x, bounds.max_y, bounds.max_z),
            dimension=dimension,
            important=True,
        )
        world.validate_bounds(bounds, dimension)

        chunks = ChunkProcessor(structure)
        jobs_iter = chain(chunks.process(), world.write(chunks, dimension))
        jobs_count = 3 * chunks.chunks_count

        with CancellableProgress("Confirm to proceed?", default=True) as progress:
            finished = progress.run(jobs_iter, jobs_count, "Generating")

        if not finished:
            raise UserCancelled
