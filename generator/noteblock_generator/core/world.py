from __future__ import annotations

import math
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from amulet import load_format
from amulet.api import Block
from amulet.api.errors import LoaderNoneMatched
from amulet.api.level import World as BaseWorld
from amulet.level.formats.anvil_world.format import AnvilFormat
from click import UsageError

from ..cli.args import Dimension, Facing, Tilt
from ..cli.console import Console
from .direction import Direction, get_nearest_direction
from .preserve_terrain import resolve_empty_block

if TYPE_CHECKING:
    from .chunks import ChunkEdits, ChunksData
    from .coordinates import XYZ, XZ, Bounds


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
        players = tuple(self.get_player(_id) for _id in self.all_player_ids())
        self.player = players[0] if players else None
        self._wrapper = format_wrapper

    def validate_bounds(self, bounds: Bounds, dimension: Dimension):
        start = (bounds.min_x, bounds.min_y, bounds.min_z)
        end = (bounds.max_x, bounds.max_y, bounds.max_z)
        Console.info(
            "Structure will occupy the space\n{start} to {end} in {dimension}.",
            start=start,
            end=end,
            dimension=dimension.name,
            important=True,
        )

        world_bounds = self.bounds(f"minecraft:{dimension.name}")
        for coord, limit, axis in [
            (bounds.min_x, world_bounds.min_x, "min X"),
            (bounds.max_x, world_bounds.max_x, "max X"),
            (bounds.min_y, world_bounds.min_y, "min Y"),
            (bounds.max_y, world_bounds.max_y, "max Y"),
            (bounds.min_z, world_bounds.min_z, "min Z"),
            (bounds.max_z, world_bounds.max_z, "max Z"),
        ]:
            if ("max" in axis and coord > limit) or ("min" in axis and coord < limit):
                raise UsageError(
                    f"Structure exceeds world boundary at {axis}: {coord} vs {limit=}."
                )

    def write(self, chunks: ChunksData, dimension: Dimension):
        for chunk_coords, data in chunks.items():
            yield self._edit_chunk(chunk_coords, data, f"minecraft:{dimension.name}")
        self._wrapper.save()

    # These cached_property aren't for performance,
    # but to ensure each Console.info is only printed once.

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

    @cached_property
    def player_dimension(self) -> Dimension:
        if self.player:
            dimension = self.player.dimension[len("minecraft:") :]
            Console.info("Using player's dimension: {dimension}", dimension=dimension)
            return Dimension(dimension)

        default = "overworld"
        Console.info(
            "Unable to read player data; dimension {dimension} is used by default.",
            dimension=default,
        )
        return Dimension(default)

    @cached_property
    def player_facing(self) -> Facing:
        if self.player:
            [horizontal_rotation, _] = self.player.rotation
            direction = get_nearest_direction(horizontal_rotation)
            Console.info(
                "Using player's facing: {direction}",
                direction=direction,
            )
            return Facing[direction.name]

        default = Direction.east
        Console.info(
            "Unable to read player data; facing {direction} is used by default.",
            direction=default,
        )
        return Facing[default.name]

    @cached_property
    def player_tilt(self) -> Tilt:
        if self.player:
            [_, vertical_rotation] = self.player.rotation
            tilt = "down" if vertical_rotation > 0 else "up"
            Console.info("Using player's tilt: {tilt}", tilt=tilt)
            return Tilt(tilt)

        default = "down"
        Console.info(
            "Unable to read player data; tilt {tilt} is used by default.",
            tilt=default,
        )
        return Tilt(default)

    def _edit_chunk(self, chunk_coords: XZ, edits: ChunkEdits, dimension: str):
        try:
            chunk = self.get_chunk(*chunk_coords, dimension)
        except Exception:
            raise ChunkLoadError(chunk_coords)

        chunk.block_entities = {}
        for coords, block in edits.items():
            if block is None:
                if (block := resolve_empty_block(chunk, coords)) is None:
                    continue
            if isinstance(block, str):
                block = Block.from_string_blockstate(f"minecraft:{block}")
            chunk.set_block(*coords, block)

        chunk.misc.pop("height_mapC", None)
        chunk.misc.pop("height_map256IA", None)
        chunk.misc.pop("block_light", None)
        chunk.misc.pop("sky_light", None)
        chunk.misc.pop("isLightOn", None)
        self._wrapper._commit_chunk(chunk, dimension)
