from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .chunks import ChunkProcessor
from .session import UserCancelled, WorldGeneratingSession
from .structure import Structure
from .utils.console import CancellableProgress, Console

if TYPE_CHECKING:
    from ..api.types import Building
    from .coordinates import XYZ, DirectionName, TiltName


def generate(
    *,
    data: Building,
    world_path: Path,
    position: XYZ | None,
    dimension: str | None,
    direction: DirectionName | None,
    tilt: TiltName | None,
    theme: str,
    blend: bool,
    use_cache: bool,
):
    if blend:
        Console.warn("Blend mode is experimental. Turn it off if you encounter issues.")

    with WorldGeneratingSession(world_path, use_cache=use_cache) as session:
        world = session.load_world()
        dimension = dimension or world.player_dimension

        structure = Structure(
            data=data,
            position=position or world.player_position,
            direction=direction or world.player_direction,
            tilt=tilt or world.player_tilt,
            theme=theme,
            blend=blend,
            cache=session.cache,
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

        with CancellableProgress("Confirm to proceed?", default=True) as progress:
            chunk_processor = ChunkProcessor(structure)

            def process():
                return progress.run(
                    chunk_processor.process(),
                    jobs_count=structure.volume,
                    description="Loading data",
                )

            def write():
                write_jobs_count = 2 * chunk_processor.chunks_count
                if not write_jobs_count:
                    if use_cache:
                        Console.info(
                            "Structure unchanged from cache. Nothing to generate.",
                            important=True,
                        )
                    else:
                        # should never happen, but just in case
                        Console.warn(
                            "The structure is empty. Nothing to generate.",
                            important=True,
                        )
                    return True

                return progress.run(
                    world.write(chunk_processor, dimension),
                    jobs_count=write_jobs_count,
                    description="Generating",
                )

            finished = process() and write()

        if not finished:
            raise UserCancelled
