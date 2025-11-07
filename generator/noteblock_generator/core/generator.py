from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, final

from .chunks import ChunksManager
from .structure import Structure
from .utils.console import Console
from .utils.progress_bar import Progress

if TYPE_CHECKING:
    from .api.types import BlockMap, BlockName, Building, Size
    from .coordinates import XYZ, DirectionName
    from .structure import AlignName, TiltName


@final
class Generator:
    _cached_size: Size | None = None
    _cached_blocks: BlockMap = {}

    def __init__(
        self,
        *,
        world_path: Path,
        coordinates: XYZ | None,
        dimension: str | None,
        facing: DirectionName | None,
        tilt: TiltName | None,
        align: AlignName,
        theme: list[BlockName],
        blend: bool,
    ):
        self.world_path = world_path
        self.coordinates = coordinates
        self.dimension = dimension
        self.facing: DirectionName | None = facing
        self.tilt: TiltName | None = tilt
        self.align: AlignName = align
        self.theme = theme
        self.blend = blend

    def run(self, *, data: Building, partial: bool):
        if not partial:
            self._generate(data.size, data.blocks)
            return

        if not self._cached_blocks:
            self._generate(data.size, data.blocks)
            self._cached_blocks = data.blocks
            Console.info("Watching for changes...")
            return

        changed_blocks: BlockMap = {
            k: v
            for k, v in data.blocks.items()
            if k not in self._cached_blocks or self._cached_blocks[k] != v
        }
        if not changed_blocks:
            return

        Console.info(
            "\n{blocks} changed from last generation.",
            blocks=f"{len(changed_blocks)} blocks",
        )
        self._generate(data.size, changed_blocks)
        self._cached_blocks.update(changed_blocks)
        Console.info("Watching for changes...")

    def _generate(self, size: Size, blocks: BlockMap):
        # importing amulet is slow, delay it until needed
        from .session import GeneratingSession, UserCancelled

        with GeneratingSession(self.world_path) as session:
            world = session.load_world()

            # if watch, use the same world params on every run
            if not self.dimension:
                self.dimension = world.player_dimension
            if not self.coordinates:
                self.coordinates = world.player_coordinates
            if not self.facing:
                self.facing = world.player_facing
            if not self.tilt:
                self.tilt = world.player_tilt

            structure = Structure(
                size=size,
                blocks=blocks,
                partial=bool(self._cached_blocks),
                coordinates=self.coordinates,
                facing=self.facing,
                tilt=self.tilt,
                align=self.align,
                theme=self.theme,
                blend=self.blend,
            )

            if size == self._cached_size:
                Console.info("Location unchanged.")
            else:
                bounds = structure.bounds
                Console.info(
                    (
                        "Location: "
                        if self._cached_size
                        else "Structure will occupy the space\n"
                    )  # simpler message on subsequent runs
                    + "{start} to {end} in {dimension}",
                    start=(bounds.min_x, bounds.min_y, bounds.min_z),
                    end=(bounds.max_x, bounds.max_y, bounds.max_z),
                    dimension=self.dimension,
                    important=not self._cached_size,
                )
                world.validate_bounds(bounds, self.dimension)
                self._cached_size = size

            # if watch, only prompt on first run
            with Progress(cancellable=not self._cached_blocks) as progress:
                chunks = ChunksManager()
                if not progress.run(
                    chunks.process(structure),
                    jobs_count=structure.blocks_count,
                    description="Calculating",
                    transient=True,
                ):
                    raise UserCancelled

                if not progress.run(
                    world.write(chunks, self.dimension),
                    jobs_count=2 * chunks.count,  # write + save
                    description=(
                        "Generating" if not self._cached_blocks else "Regenerating"
                    ),
                    transient=False,
                ):
                    raise UserCancelled
