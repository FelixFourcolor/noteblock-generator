from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, final

import watchfiles
from click import UsageError

from .api.loader import load
from .chunks import ChunkProcessor
from .session import GeneratingSession, UserCancelled
from .structure import Structure
from .utils.console import Console
from .utils.progress_bar import Progress

if TYPE_CHECKING:
    from .api.types import BlockMap, BlockName, Size
    from .coordinates import XYZ, DirectionName
    from .structure import AlignName, TiltName


@final
class Generator:
    _cache: BlockMap = {}

    def __init__(
        self,
        *,
        world_path: Path,
        input_path: Path | None,
        coordinates: XYZ | None,
        dimension: str | None,
        facing: DirectionName | None,
        tilt: TiltName | None,
        align: AlignName,
        theme: list[BlockName],
        blend: bool,
    ):
        self.input_path = input_path
        self.world_path = world_path
        self.coordinates = coordinates
        self.dimension = dimension
        self.facing: DirectionName | None = facing
        self.tilt: TiltName | None = tilt
        self.align: AlignName = align
        self.theme = theme
        self.blend = blend

    def run(self, *, watch: bool):
        if not watch:
            self._run_once()
            return

        if not self.input_path:
            raise UsageError("--watch requires input file path.")

        self._cache = self._run_once()
        Console.info("Watching for changes...")
        for _ in watchfiles.watch(self.input_path):
            self._run_with_cache()

    def _run_once(self):
        data = self._load()
        self._generate(data.size, data.blocks)
        return data.blocks

    def _run_with_cache(self):
        try:
            data = self._load()
        except Exception:
            # in case file temporarily becomes invalid, just skip this change
            return

        changed_blocks: BlockMap = {
            k: v
            for k, v in data.blocks.items()
            if k not in self._cache or self._cache[k] != v
        }
        if not changed_blocks:
            return

        Console.clear()
        Console.info(
            "{blocks} changed from last generation.",
            blocks=f"{len(changed_blocks)} blocks",
        )
        self._generate(data.size, changed_blocks)
        self._cache.update(changed_blocks)
        Console.info("Watching for changes...")

    def _load(self):
        try:
            data = load(self.input_path)
        except Exception:
            raise UsageError("Invalid input data.")
        if not data:
            raise UsageError(
                "Missing input: Either provide file path with --in, or pipe content to stdin.",
            )
        return data

    def _generate(self, size: Size, blocks: BlockMap):
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
                partial=bool(self._cache),
                coordinates=self.coordinates,
                facing=self.facing,
                tilt=self.tilt,
                align=self.align,
                theme=self.theme,
                blend=self.blend,
            )

            bounds = structure.bounds
            Console.info(
                "Structure will occupy the space"
                + ("\n" if not self._cache else " ")
                + "{start} to {end} in {dimension}.",
                start=(bounds.min_x, bounds.min_y, bounds.min_z),
                end=(bounds.max_x, bounds.max_y, bounds.max_z),
                dimension=self.dimension,
                important=not self._cache,
            )
            world.validate_bounds(structure.bounds, self.dimension)

            with Progress(
                cancellable=not self._cache  # if watch, only prompt on first run
            ) as progress:
                chunks = ChunkProcessor(structure)
                if not progress.run(
                    chunks.process(),
                    jobs_count=structure.blocks_count,
                    description="Calculating",
                    transient=True,
                ):
                    raise UserCancelled

                if not progress.run(
                    world.write(chunks, self.dimension),
                    jobs_count=2 * chunks.count,
                    description="Generating" if not self._cache else "Updating",
                    transient=False,
                ):
                    raise UserCancelled
