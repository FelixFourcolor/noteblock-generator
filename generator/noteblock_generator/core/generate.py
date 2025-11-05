from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING

from .cache import Cache
from .chunks import ChunkProcessor
from .session import GeneratingSession, UserCancelled
from .structure import Structure
from .utils.progress_bar import Progress

if TYPE_CHECKING:
    from ..api.types import BlockName, Building
    from .coordinates import XYZ, DirectionName
    from .structure import AlignName, TiltName


def generate(
    *,
    data: Building,
    world_path: Path,
    coordinates: XYZ | None,
    dimension: str | None,
    facing: DirectionName | None,
    tilt: TiltName | None,
    align: AlignName,
    theme: list[BlockName],
    blend: bool,
    partial: bool,
):
    if not partial:
        Cache.delete(world_path=world_path)
        cache_context = nullcontext()
    else:
        cache_context = Cache(
            world_path=world_path,
            key=Cache.get_key(
                coordinates=coordinates,
                dimension=dimension,
                facing=facing,
                tilt=tilt,
                align=align,
                theme=theme,
                blend=blend,
            ),
        )

    with cache_context as cache:
        if not cache:
            blocks = data.blocks
        else:
            if not (blocks := cache.update(blocks=data.blocks)):
                return
            partial = cache.has_data()

        with GeneratingSession(world_path) as session:
            world = session.load_world()
            dimension = dimension or world.player_dimension
            structure = Structure(
                size=data.size,
                blocks=blocks,
                coordinates=coordinates or world.player_coordinates,
                facing=facing or world.player_facing,
                tilt=tilt or world.player_tilt,
                align=align,
                theme=theme,
                blend=blend,
                partial=partial,
            )
            chunks = ChunkProcessor(structure)

            # no need to validate bounds or confirm for partial updates,
            # because boundaries already validated and user already confirmed last time
            if not partial:
                world.validate_bounds(structure.bounds, dimension)

            with Progress(cancellable=not partial) as progress:
                if not progress.run(
                    chunks.process(),
                    jobs_count=structure.blocks_count,
                    description="Calculating",
                    transient=True,
                ):
                    raise UserCancelled

                if not progress.run(
                    world.write(chunks, dimension),
                    jobs_count=2 * chunks.count,
                    description="Generating" + (" the difference" if partial else ""),
                    transient=False,
                ):
                    raise UserCancelled
