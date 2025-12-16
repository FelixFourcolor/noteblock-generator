from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from amulet.api.chunk import Chunk

    from .coordinates import XYZ


_LIQUID = {
    "lava",
    "water",
    "ice",
    "bubble_column",
    "kelp",
    "kelp_plant",
    "seagrass",
    "tall_seagrass",
}

_FALLING = {
    "anvil",
    "chipped_anvil",
    "damaged_anvil",
    "white_concrete_powder",
    "orange_concrete_powder",
    "magenta_concrete_powder",
    "light_blue_concrete_powder",
    "yellow_concrete_powder",
    "lime_concrete_powder",
    "pink_concrete_powder",
    "gray_concrete_powder",
    "light_gray_concrete_powder",
    "cyan_concrete_powder",
    "purple_concrete_powder",
    "blue_concrete_powder",
    "brown_concrete_powder",
    "green_concrete_powder",
    "red_concrete_powder",
    "black_concrete_powder",
    "dragon_egg",
    "gravel",
    "sand",
    "red_sand",
    "scaffolding",
}

_REDSTONES = {
    "calibrated_sculk_sensor",
    "comparator",
    "jukebox",
    "note_block",
    "observer",
    "piston",
    "red_sand",
    "redstone_block",
    "redstone_torch",
    "redstone_wire",
    "repeater",
    "sculk_sensor",
    "sticky_piston",
    "tnt",
    "tnt_minecart",
}

DANGER_LIST = _LIQUID | _FALLING | _REDSTONES


def resolve_empty_block(chunk: Chunk, coords: XYZ):
    block = chunk.get_block(*coords)
    name = block.base_name

    if name in DANGER_LIST:
        return "air"

    if block.extra_blocks:
        return block.base_block

    try:
        if getattr(block, "waterlogged"):
            return name
    except AttributeError:
        pass
