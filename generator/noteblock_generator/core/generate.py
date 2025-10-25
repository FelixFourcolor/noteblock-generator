from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING

from .cache import Cache
from .chunks import ChunkProcessor
from .session import GeneratingSession, UserCancelled
from .structure import Structure
from .utils.console import CancellableProgress

if TYPE_CHECKING:
    from ..api.types import Building
    from .coordinates import XYZ, DirectionName
    from .structure import AlignName, TiltName


def generate(
    *,
    data: Building,
    world_path: Path,
    position: XYZ | None,
    dimension: str | None,
    facing: DirectionName | None,
    tilt: TiltName | None,
    align: AlignName,
    theme: str,
    blend: bool,
    walkable: bool,
    partial: bool,
):
    if not partial:
        Cache.delete(key=world_path)

    with Cache(key=world_path) if partial else nullcontext() as cache:
        with GeneratingSession(world_path) as session:
            world = session.load_world()
            dimension = dimension or world.player_dimension
            structure = Structure(
                data=data,
                position=position or world.player_coordinates,
                facing=facing or world.player_facing,
                tilt=tilt or world.player_tilt,
                align=align,
                theme=theme,
                blend=blend,
                walkable=walkable,
                cache=cache,
            )
            world.validate_bounds(structure.bounds, dimension)

            chunks = ChunkProcessor(structure)
            with CancellableProgress("Confirm to proceed?", default=True) as progress:
                if not progress.run(
                    chunks.process(),
                    jobs_count=structure.volume,
                    description="Calculating",
                    cancellable=False,
                ):
                    raise UserCancelled

                if cache:
                    cache.display_stats()

                write_jobs_count = 2 * chunks.count
                if not write_jobs_count:
                    # when partial update and nothing has changed
                    return

                if not progress.run(
                    world.write(chunks, dimension),
                    jobs_count=write_jobs_count,
                    description="Generating"
                    + (" the difference" if cache and cache.has_data else ""),
                ):
                    raise UserCancelled
