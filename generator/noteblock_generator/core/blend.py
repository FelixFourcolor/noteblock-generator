from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from amulet.api.chunk import Chunk

    from .coordinates import XYZ


_LIQUID = {
    "lava",
    "water",
    "bubble_column",
    "kelp",
    "kelp_plant",
    "seagrass",
    "tall_seagrass",
}

_GRAVITY_AFFECTED = {
    "anvil",
    "concrete_powder",
    "dragon_egg",
    "gravel",
    "pointed_dripstone",
    "sand",
    "scaffolding",
    "snow",
    "suspicious_sand",
    "suspicious_gravel",
}

_REDSTONE_COMPONENTS = {
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

DANGER_LIST = _LIQUID | _GRAVITY_AFFECTED | _REDSTONE_COMPONENTS


def blend_filter(chunk: Chunk, coords: XYZ):
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
