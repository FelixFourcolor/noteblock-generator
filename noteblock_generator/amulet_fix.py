# Copyright Amulet Team. (https://www.amuletmc.com/)
# LICENSE: https://github.com/Amulet-Team/Amulet-Core/blob/update-licence-info-2/LICENSE

# type: ignore
# ruff: noqa

"""Fixes https://github.com/Amulet-Team/Amulet-Core/issues/276.
The bug has been fixed upstream, but its commit hasn't been published to PyPI.
This file contains the fix commit.
"""

from amulet.level.formats.anvil_world.format import *
from amulet_nbt import FloatTag


class FixedAnvilFormat(AnvilFormat):
    def _load_player(self, player_id: str) -> Player:
        player_nbt = self._get_raw_player_data(player_id)
        dimension = player_nbt["Dimension"]
        # TODO: rework this when there is better dimension support.
        if isinstance(dimension, IntTag):
            if -1 <= dimension.py_int <= 1:
                dimension_str = {-1: THE_NETHER, 0: OVERWORLD, 1: THE_END}[
                    dimension.py_int
                ]
            else:
                dimension_str = f"DIM{dimension}"
        elif isinstance(dimension, StringTag):
            dimension_str = dimension.py_str
        else:
            dimension_str = OVERWORLD
        if dimension_str not in self._dimension_name_map:
            dimension_str = OVERWORLD

        # get the players position
        pos_data = player_nbt.get("Pos")
        if (
            isinstance(pos_data, ListTag)
            and len(pos_data) == 3
            and pos_data.list_data_type == DoubleTag.tag_id
        ):
            position = tuple(map(float, pos_data))
            position = tuple(
                p if -100_000_000 <= p <= 100_000_000 else 0.0 for p in position
            )
        else:
            position = (0.0, 0.0, 0.0)

        # get the players rotation
        rot_data = player_nbt.get("Rotation")
        if (
            isinstance(rot_data, ListTag)
            and len(rot_data) == 2
            and rot_data.list_data_type == FloatTag.tag_id
        ):
            rotation = tuple(map(float, rot_data))
            rotation = tuple(
                p if -100_000_000 <= p <= 100_000_000 else 0.0 for p in rotation
            )
        else:
            rotation = (0.0, 0.0)

        return Player(
            player_id,
            dimension_str,
            position,
            rotation,
        )
