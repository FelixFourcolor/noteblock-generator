from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .cache import Cache
from .chunks import ChunkProcessor
from .session import GeneratingSession, UserCancelled
from .structure import Structure
from .utils.console import CancellableProgress

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
    partial: bool,
):
    with Cache(world_path, enabled=partial) as cache:
        with GeneratingSession(world_path) as session:
            world = session.load_world()
            dimension = dimension or world.player_dimension
            structure = Structure(
                data=data,
                position=position or world.player_position,
                direction=direction or world.player_direction,
                tilt=tilt or world.player_tilt,
                theme=theme,
                blend=blend,
                cache=cache,
            )
            world.validate_bounds(structure.bounds, dimension)

            chunks = ChunkProcessor(structure)
            with CancellableProgress("Confirm to proceed?", default=True) as progress:
                if not progress.run(
                    chunks.process(),
                    jobs_count=structure.volume,
                    description="Calculating",
                    transient=True,
                ):
                    raise UserCancelled

                if cache:
                    cache.display_stats()

                if write_jobs_count := 2 * chunks.count:
                    description = "Generating" + (
                        " the difference" if cache and cache.has_data else ""
                    )
                    if not progress.run(
                        world.write(chunks, dimension),
                        jobs_count=write_jobs_count,
                        description=description,
                    ):
                        raise UserCancelled
