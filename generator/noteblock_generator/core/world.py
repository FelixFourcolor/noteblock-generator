from __future__ import annotations

import math
from functools import cache, cached_property
from pathlib import Path
from typing import TYPE_CHECKING, cast

from amulet import StringTag, load_format
from amulet.api import Block
from amulet.api.errors import LoaderNoneMatched
from amulet.api.level import World as BaseWorld
from amulet.level.formats.anvil_world.format import AnvilFormat
from click import UsageError

from noteblock_generator.core.api.types import BlockName

from .blend import blend_filter
from .coordinates import Direction, get_nearest_direction
from .utils.console import Console
from .utils.iter import exhaust

if TYPE_CHECKING:
    from amulet.api.chunk import Chunk

    from .chunks import ChunkPlacement, ChunksManager
    from .coordinates import XYZ, XZ, DirectionName
    from .structure import Bounds, TiltName


class ChunkLoadError(Exception):
    def __init__(self, chunk_coords: XZ):
        super().__init__("")
        cx, cz = chunk_coords
        self.coordinates = (cx << 4, cz << 4)


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

    def __hash__(self):
        return 0

    def validate_bounds(self, bounds: Bounds, dimension: str):
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
                f"Structure exceeds world boundary at {axis}: {coord} vs {limit=}.",
            )

    def write(self, chunks: ChunksManager, dimension: str):
        dimension = "minecraft:" + dimension
        for chunk_coords, data in chunks:
            self._modify_chunk(chunk_coords, data, dimension=dimension)
            yield

        yield from self._save(dimension=dimension)

    @cached_property
    def player_coordinates(self) -> XYZ:
        if self.player:
            [x, y, z] = tuple(map(math.floor, self.player.location))
            Console.info("Using player's coordinates: {location}", location=(x, y, z))
            return (x, y, z)

        default = (0, 63, 0)
        Console.info(
            "Unable to read player data; coordinates {location} is used by default.",
            location=default,
        )
        return default

    # These cached_property aren't for performance,
    # but so that the Console.info are only printed once.

    @cached_property
    def player_dimension(self) -> str:
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
    def player_facing(self) -> DirectionName:
        if self.player:
            [horizontal_rotation, _] = self.player.rotation
            direction = get_nearest_direction(horizontal_rotation)
            Console.info(
                "Using player's facing: {direction}",
                direction=direction,
            )
            return direction.name

        default = Direction.east
        Console.info(
            "Unable to read player data; facing {direction} is used by default.",
            direction=default,
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

    @cache  # this one is actually for performance
    def create_block(self, block: BlockName) -> Block:
        return Block("minecraft", *parse_block(block))

    def _modify_chunk(
        self, chunk_coords: XZ, mods: ChunkPlacement, dimension: str
    ) -> None:
        try:
            chunk = self.get_chunk(*chunk_coords, dimension)
        except Exception:
            raise ChunkLoadError(chunk_coords)

        chunk.block_entities = {}
        self._modified_chunks[chunk_coords] = chunk

        for coords, block_name in mods.items():
            if block_name is None:
                block = blend_filter(chunk, coords)
                if isinstance(block, str):
                    block = self.create_block(block)
            else:
                block = self.create_block(block_name)

            if block is not None:
                chunk.set_block(*coords, block)

    def _save(self, dimension: str):
        wrapper = cast(AnvilFormat, self.level_wrapper)
        for (x, z), chunk in self._modified_chunks.items():
            dimension_chunk = (dimension, x, z)
            exhaust(
                wrapper._calculate_height(self, [dimension_chunk]),
                wrapper._calculate_light(self, [dimension_chunk]),
            )
            wrapper.commit_chunk(chunk, dimension)
            yield

        self.history_manager.mark_saved()
        wrapper.save()


def parse_block(block: BlockName) -> tuple[str, dict[str, StringTag]]:
    if "[" not in block:
        return block, {}

    name, props_str = block.split("[", 1)
    props_str = props_str.rstrip("]")
    properties = {
        key: StringTag(value)
        for prop in props_str.split(",")
        for key, value in [prop.split("=", 1)]
    }
    return name, properties
