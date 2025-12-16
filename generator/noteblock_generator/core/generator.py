from __future__ import annotations

from functools import cached_property
from itertools import product
from typing import TYPE_CHECKING

from ..cli.console import Console
from ..cli.progress_bar import ProgressBar
from .blocks import BlockMapper
from .chunks import organize_chunks
from .coordinates import CoordinateTranslator
from .direction import Direction
from .placement import PlacementConfig
from .session import GeneratingSession

if TYPE_CHECKING:
    from ..cli.args import Align, Dimension, Facing, Tilt, Walkable
    from ..data.schema import BlockMap, BlockState, Building, Size
    from .coordinates import XYZ
    from .world import World


class Generator:
    def __init__(
        self,
        *,
        session: GeneratingSession,
        coordinates: XYZ | None,
        dimension: Dimension | None,
        facing: Facing | None,
        tilt: Tilt | None,
        align: Align,
        theme: list[BlockState],
        walkable: Walkable,
        preserve_terrain: bool,
    ):
        self.session = session
        self.coordinates = coordinates
        self.dimension = dimension
        self.facing = facing
        self.tilt = tilt
        self.align = align
        self.theme = theme
        self.walkable = walkable
        self.preserve_terrain = preserve_terrain

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

    @cached_property
    def _config(self):
        assert self.coordinates is not None
        assert self.facing is not None
        assert self.tilt is not None

        return PlacementConfig(
            origin=self.coordinates,
            direction=Direction[self.facing.name],
            tilt=self.tilt,
            align=self.align,
            theme=self.theme,
            walkable=self.walkable,
            preserve_terrain=self.preserve_terrain,
        )

    @cached_property
    def _block_mapper(self) -> BlockMapper:
        return BlockMapper(self._config)

    @cached_property
    def _coordinate_translator(self) -> CoordinateTranslator:
        return CoordinateTranslator(self._config)

    def _generate(self, size: Size, blocks: BlockMap):
        is_first_run = self._prev_size is None

        with self.session as world:
            if is_first_run:
                self._initialize_world_params(world)
            assert self.dimension is not None

            self._block_mapper.update_size(size)
            self._coordinate_translator.update_size(size)

            if size != self._prev_size:
                bounds = self._coordinate_translator.calculate_bounds()
                world.validate_bounds(bounds, self.dimension)

            with ProgressBar(cancellable=is_first_run) as track:
                description = "Generating" if is_first_run else "Regenerating"
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
                    self._coordinate_translator.get((x, y, z)),
                    self._block_mapper.resolve(block, (x, y, z)),
                )
            return

        if empty_blocks := self._block_mapper.calculate_expansion(self._prev_size):
            blocks = {**empty_blocks, **blocks}

        for str_coords, block in blocks.items():
            x, y, z = map(int, str_coords.split(" "))
            yield (
                self._coordinate_translator.get((x, y, z)),
                self._block_mapper.resolve(block, (x, y, z)),
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
