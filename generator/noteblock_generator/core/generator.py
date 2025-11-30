from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import TYPE_CHECKING

from ..cli.console import Console
from ..cli.progress_bar import ProgressBar
from .blocks import BlockTranslator
from .chunks import organize_chunks
from .coordinates import CoordinateTranslator
from .direction import Direction
from .placement import PlacementConfig

if TYPE_CHECKING:
    from ..data.schema import BlockMap, BlockState, Building, Size
    from .coordinates import XYZ, DirectionName
    from .placement import AlignName, TiltName
    from .world import World


class Generator:
    def __init__(
        self,
        *,
        world_path: Path,
        coordinates: XYZ | None,
        dimension: str | None,
        facing: DirectionName | None,
        tilt: TiltName | None,
        align: AlignName,
        theme: list[BlockState],
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

        self._prev_size: Size | None = None
        self._cached_blocks: BlockMap = {}

    def generate(self, data: Building, *, cached=False):
        blocks: BlockMap = data.blocks
        size = data.size

        if cached and self._cached_blocks:
            blocks = {
                k: v for k, v in blocks.items() if self._cached_blocks.get(k) != v
            }
            if not blocks:
                Console.info("No changes from last generation.")
                return
            Console.info(
                "{blocks} changed from last generation.", blocks=f"{len(blocks)} blocks"
            )

        self._generate(size, blocks)

        if cached:
            self._cached_blocks |= blocks
            self._prev_size = size

    def _generate(self, size: Size, blocks: BlockMap):
        # importing amulet is slow, delay it until needed
        from .session import GeneratingSession

        is_first_run = self._prev_size is None

        with GeneratingSession(self.world_path) as session:
            world = session.load_world()
            if is_first_run:
                self._initialize_world_params(world)
            assert self.dimension is not None

            self._block_translator.update_size(size)
            self._coordinate_translator.update_size(size)

            if size != self._prev_size:
                bounds = self._coordinate_translator.calculate_bounds()
                world.validate_bounds(bounds, self.dimension)

            with ProgressBar(cancellable=is_first_run) as track:
                description = "Generating" if is_first_run else "Updating"
                block_placements = self._get_block_placements(size, blocks)
                chunks = track(
                    organize_chunks(block_placements),
                    description=description,
                    transient=True,
                )
                track(
                    world.write(chunks, self.dimension),
                    description=description,
                    jobs_count=len(chunks),
                    transient=not is_first_run,
                )

    def _get_block_placements(self, size: Size, blocks: BlockMap):
        if self._prev_size is None:
            for x, y, z in product(
                range(size.length), range(size.height), range(size.width)
            ):
                block = blocks.get(f"{x} {y} {z}")
                yield (
                    self._coordinate_translator[x, y, z],
                    self._block_translator[block, z],
                )
            return

        fill_blocks = self._block_translator.calculate_fill(self._prev_size)
        if fill_blocks:
            blocks = {**fill_blocks, **blocks}

        for str_coords, block in blocks.items():
            x, y, z = map(int, str_coords.split(" "))
            yield (
                self._coordinate_translator[x, y, z],
                self._block_translator[block, z],
            )

    def _initialize_world_params(self, world: World):
        if not self.dimension:
            self.dimension = world.player_dimension
        if not self.coordinates:
            self.coordinates = world.player_coordinates
        if not self.facing:
            self.facing = world.player_facing
        if not self.tilt:
            self.tilt = world.player_tilt

        config = PlacementConfig(
            origin=self.coordinates,
            facing=Direction[self.facing],
            tilt=self.tilt,
            align=self.align,
            theme=self.theme,
            blend=self.blend,
        )
        self._block_translator = BlockTranslator(config)
        self._coordinate_translator = CoordinateTranslator(config)
