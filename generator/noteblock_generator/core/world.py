from __future__ import annotations

import math
from collections import deque
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, cast, final

from amulet import StringTag, load_format
from amulet.api import Block
from amulet.api.errors import ChunkLoadError, LoaderNoneMatched
from amulet.api.level import World as BaseWorld
from amulet.level.formats.anvil_world.format import AnvilFormat
from click import UsageError
from typing_extensions import override

from .blend import blend_filter
from .coordinates import Direction, get_nearest_direction
from .utils.console import Console

if TYPE_CHECKING:
    from amulet.api.chunk import Chunk

    from .chunks import ChunkPlacement, ChunkProcessor
    from .coordinates import XZ, DirectionName, TiltName
    from .structure import Bounds


@final
class World(BaseWorld):
    @classmethod
    def load(cls, world_path: str | Path) -> World:
        world_path = str(world_path)
        try:
            format_wrapper = load_format(world_path)
        except LoaderNoneMatched:
            raise UsageError(
                "Unrecognized world format. Are you sure that's a valid Minecraft save?"
            )
        if not isinstance(format_wrapper, AnvilFormat):
            raise UsageError("Unsupported world format; expected Java Edition.")

        return cls(world_path, format_wrapper)

    def __init__(self, directory: str, format_wrapper: AnvilFormat):
        super().__init__(directory, format_wrapper)
        self.path = directory
        self.block_translator = self.translation_manager.get_version(
            "java", (1, 21)
        ).block
        players = tuple(self.get_player(_id) for _id in self.all_player_ids())
        self.player = players[0] if players else None
        self._modified_chunks: dict[XZ, Chunk] = {}

    @override
    def __hash__(self):
        return hash(self.path)

    def validate_bounds(self, bounds: Bounds, dimension: str):
        Console.info(
            "Structure will occupy the space\n{start} to {end} in {dimension}.",
            start=(bounds.min_x, bounds.min_y, bounds.min_z),
            end=(bounds.max_x, bounds.max_y, bounds.max_z),
            dimension=dimension,
            important=True,
        )

        world_bounds = self.bounds("minecraft:" + dimension)
        for coord, limit, axis in [
            (bounds.min_x, world_bounds.min_x, "min_x"),
            (bounds.max_x, world_bounds.max_x, "max_x"),
            (bounds.min_y, world_bounds.min_y, "min_y"),
            (bounds.max_y, world_bounds.max_y, "max_y"),
            (bounds.min_z, world_bounds.min_z, "min_z"),
            (bounds.max_z, world_bounds.max_z, "max_z"),
        ]:
            if ("min" in axis and coord >= limit) or ("max" in axis and coord <= limit):
                continue
            raise UsageError(
                f"Structure exceeds world boundary at {axis}: {coord} vs {limit}.",
            )

    def write(self, chunks: ChunkProcessor, dimension: str):
        dimension = "minecraft:" + dimension
        for chunk_coords, data in chunks:
            self._modify_chunk(chunk_coords, data, dimension=dimension)
            yield

        yield from self._save(dimension=dimension)

    @cached_property
    def player_position(self):
        if self.player:
            [x, y, z] = tuple(map(math.floor, self.player.location))
            Console.info("Using player's position: {position}", position=(x, y, z))
            return (x, y, z)

        default = (0, 63, 0)
        Console.info(
            "Unable to read player data; position {location} is used by default.",
            location=default,
        )
        return default

    @cached_property
    def player_dimension(self):
        if self.player:
            dimension = self.player.dimension[len("minecraft:") :]
            Console.info("Using player's dimension: {dimension}", dimension=dimension)
            return dimension

        default = "overworld"
        Console.info(
            "Unable to read player data; dimension {dimension} is used by default.",
            dimension=default,
        )
        return default

    @cached_property
    def player_direction(self) -> DirectionName:
        if self.player:
            [horizontal_rotation, _] = self.player.rotation
            direction = get_nearest_direction(horizontal_rotation)
            Console.info(
                "Using player's direction: {direction}",
                direction=f"{direction.name} ({direction.description})",
            )
            return direction.name

        default = Direction.east
        Console.info(
            "Unable to read player data; facing {direction} is used by default.",
            direction=f"{default.name} ({default.description})",
        )
        return default.name

    @cached_property
    def player_tilt(self) -> TiltName:
        if self.player:
            [_, vertical_rotation] = self.player.rotation
            tilt = "down" if vertical_rotation > 0 else "up"
            Console.info("Using player's tilt: {tilt}", tilt=tilt)
            return tilt

        default = "down"
        Console.info(
            "Unable to read player data; tilt {tilt} is used by default.",
            tilt=default,
        )
        return default

    def create_block(self, name: str, **properties) -> Block:
        properties = {k: StringTag(v) for k, v in properties.items()}
        block = Block("minecraft", name, properties)
        return self.block_translator.to_universal(block)[0]

    def _modify_chunk(
        self, chunk_coords: XZ, mods: ChunkPlacement, dimension: str
    ) -> None:
        try:
            chunk = self.get_chunk(*chunk_coords, dimension)
        except ChunkLoadError:
            chunk = self.create_chunk(*chunk_coords, dimension)
        chunk.block_entities = {}
        self._modified_chunks[chunk_coords] = chunk

        for coords, block_data in mods.items():
            if block_data is None:
                block = blend_filter(chunk, coords)
                if isinstance(block, str):
                    block = self.create_block(block)
            else:
                block = self.create_block(block_data.name, **block_data.properties)

            if block is not None:
                chunk.set_block(*coords, block)

    def _save(self, dimension: str):
        wrapper = cast(AnvilFormat, self.level_wrapper)
        for (x, z), chunk in self._modified_chunks.items():
            deque(wrapper._calculate_height(self, [(dimension, x, z)]), maxlen=0)
            deque(wrapper._calculate_light(self, [(dimension, x, z)]), maxlen=0)
            wrapper.commit_chunk(chunk, dimension)
            yield

        self.history_manager.mark_saved()
        wrapper.save()
