from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

from .cache import Cache
from .chunks import ChunkProcessor
from .session import GeneratingSession, UserCancelled
from .structure import Structure
from .utils.progress_bar import CancellableProgress, progress_bar

if TYPE_CHECKING:
    from ..api.types import BlockName, Building
    from .coordinates import XYZ, DirectionName
    from .structure import AlignName, TiltName

    class Customization(TypedDict):
        coordinates: XYZ
        facing: DirectionName
        tilt: TiltName
        align: AlignName
        theme: list[BlockName]
        blend: bool


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
    with GeneratingSession(world_path) as session:
        world = session.load_world()
        dimension = dimension or world.player_dimension
        coordinates = coordinates or world.player_coordinates
        facing = facing or world.player_facing
        tilt = tilt or world.player_tilt

        customization: Customization = {
            "coordinates": coordinates,
            "facing": facing,
            "tilt": tilt,
            "align": align,
            "theme": theme,
            "blend": blend,
        }
        cache_key = Cache.get_key(
            world_path=str(world_path),
            dimension=dimension,
            **customization,
        )

        if not partial:
            Cache.delete(cache_key)
            cache = None
            blocks = data.blocks
        else:
            cache = Cache(cache_key)
            blocks = cache.update(blocks=data.blocks)
            if not blocks:
                return
            partial = cache.has_data()

        structure = Structure(
            size=data.size,
            blocks=blocks,
            partial=partial,
            **customization,
        )
        chunks = ChunkProcessor(structure)

        if partial:
            # no need to validate bounds or confirm,
            # because boundaries already validated and user already confirmed last time
            progress_bar(
                chunks.process(),
                jobs_count=structure.blocks_count,
                description="Calculating",
                transient=True,
            )
            progress_bar(
                world.write(chunks, dimension),
                jobs_count=2 * chunks.count,  # write + save
                description="Generating the difference",
            )
            if cache:
                cache.save()
            return

        world.validate_bounds(structure.bounds, dimension)

        with CancellableProgress("Confirm to proceed?", default=True) as progress:
            if not progress.run(
                chunks.process(),
                jobs_count=structure.blocks_count,
                description="Calculating",
                cancellable=False,
            ):
                raise UserCancelled

            if not progress.run(
                world.write(chunks, dimension),
                jobs_count=2 * chunks.count,
                description="Generating",
            ):
                raise UserCancelled

        if cache:
            cache.save()
