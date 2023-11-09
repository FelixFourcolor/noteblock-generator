# Copyright Felix Fourcolor 2023. CC0-1.0 license

import math
from dataclasses import dataclass
from functools import cache
from typing import Optional

from .main import Location, Orientation, logger
from .parser import Composition, Note, UserError, Voice
from .utils import UserPrompt, progress_bar
from .world import (
    Block,
    BlockType,
    Direction,
    NoteBlock,
    PlacementType,
    Redstone,
    Repeater,
    World,
)

# Blocks to be removed if using blend mode,
# since they may interfere with redstones and/or noteblocks.
_LIQUID = {
    # these would destroy our redstone components if interacted
    "lava",
    "water",
    # these are always waterlogged and it's impossible to remove water from them
    # so practically treat them as water
    "bubble_column",
    "kelp",
    "kelp_plant",
    "seagrass",
    "tall_seagrass",
}
_GRAVITY_AFFECTED_BLOCKS = {
    # these may fall on top of noteblocks and prevent them to play
    "anvil",
    "concrete_powder",
    "dragon_egg",
    "gravel",
    "pointed_dripstone",
    "sand",
    "scaffolding",
    "suspicious_sand",
    "suspicious_gravel",
}

_REDSTONE_COMPONENTS = {
    # these either emit redstone signals or activated by redstone signals,
    # either of which may mess up with the music performance
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
REMOVE_LIST = _LIQUID | _GRAVITY_AFFECTED_BLOCKS | _REDSTONE_COMPONENTS

AIR = Block("air")
GLASS = Block("glass")

NOTE_LENGTH = 2  # noteblock + repeater
DIVISION_WIDTH = 5  # 4 noteblocks (maximum dynamic range) + 1 stone
VOICE_HEIGHT = 2  # noteblock + air above
DIVISION_CHANGING_LENGTH = 2  # how many blocks it takes to wrap around each bar

ROTATION = {
    -180: Direction.north,
    -90: Direction.east,
    0: Direction.south,
    90: Direction.west,
    180: Direction.north,
}


@dataclass(kw_only=True)
class Generator:
    world: World
    composition: Composition
    location: Location
    dimension: Optional[str]
    orientation: Orientation
    theme: str
    blend: bool
    no_confirm: bool

    def __call__(self):
        with self.world:
            self.parse_args()
            user_prompt = self.get_user_confirmation()
            # start generating while waiting for user input, just don't save yet.
            # If user denies, KeyboardInterrupt will be raised,
            # hence put the whole generator inside a try-catch block.
            try:
                progress_bar(0, 1, text="Generating")
                self.generate_composition()
                self.generate_init_system()
                self.world.apply_modifications()
                if user_prompt is not None:
                    user_prompt.wait()
                modified_by_another_process = self.world.save()
            except KeyboardInterrupt:
                print()
                logger.info("Aborted.")
                logger.disabled = True
            else:
                logger.info("Finished.")
                if modified_by_another_process:
                    logger.warning(
                        "If you are currently inside the world, "
                        "exit and re-enter to see the result."
                    )

    # Rotation system
    def rotate(self, coordinates: tuple[int, int, int]):
        x, y, z = coordinates
        # BUG: I don't know why but this rotation must be negated
        delta_x, delta_z = -self._rotation * (self.X - x, self.Z - z)
        return self.X + delta_x, y, self.Z + delta_z

    @cache
    def Redstone(self, *connections: Direction):
        return Redstone(*[self._rotation * c for c in connections])

    @cache
    def Repeater(self, delay: int, direction: Direction):
        return Repeater(delay=delay, direction=self._rotation * direction)

    def Button(self, facing: Direction, **kwargs):
        return Block("oak_button", facing=self._rotation * facing, **kwargs)

    def __getitem__(self, coordinates: tuple[int, int, int]):
        return self.world[self.rotate(coordinates)]

    def __setitem__(self, coordinates: tuple[int, int, int], block: PlacementType):
        self.world[self.rotate(coordinates)] = block

    def __hash__(self):
        return 0

    # generator subroutines

    def parse_args(self):
        # theme
        self.theme_block = Block(self.theme)

        # location
        self.X, self.Y, self.Z = self.location
        if self.location.x.relative:
            self.X += self.world.player_location[0]
        if self.location.y.relative:
            self.Y += self.world.player_location[1]
        if self.location.z.relative:
            self.Z += self.world.player_location[2]

        # dimension
        if self.dimension is None:
            self.dimension = self.world.player_dimension
        self.world.dimension = self.dimension

        # orientation
        self.x_direction = Direction((1, 0))
        self.z_direction = Direction((0, 1))
        h_rotation, v_rotation = self.orientation
        if h_rotation.relative:
            h_rotation += self.world.player_orientation[0]
        if v_rotation.relative:
            v_rotation += self.world.player_orientation[1]
        if not (-180 <= h_rotation <= 180):
            raise UserError("Horizontal orientation must be between -180 and 180")
        if not (-90 <= v_rotation <= 90):
            raise UserError("Vertical orientation must be between -90 and 90")
        self._rotation = (
            Direction((-1, 0))
            * ROTATION[min(ROTATION.keys(), key=lambda x: abs(x - h_rotation))]
        )
        if v_rotation >= 0:
            self.y_glass = self.Y - 1
        else:
            self.y_glass = self.Y + VOICE_HEIGHT * (self.composition.size + 1)
        self.noteblock_order = [
            -self.x_direction,
            self.x_direction,
            -self.x_direction * 2,
            self.x_direction * 2,
        ]

        # validate that coordinates are in bounds
        self.X_BOUNDARY = self.composition.length * DIVISION_WIDTH + 1
        self.Z_BOUNDARY = (
            self.composition.division * NOTE_LENGTH + DIVISION_CHANGING_LENGTH + 2
        )
        Y_BOUNDARY = VOICE_HEIGHT * (self.composition.size + 1)
        BOUNDS = self.world.bounds
        min_x, max_x = self.X, self.X + self.X_BOUNDARY
        min_z = self.Z
        if len(self.composition) == 1:
            max_z = self.Z + self.Z_BOUNDARY
        else:
            max_z = self.Z + 2 * self.Z_BOUNDARY
        min_y, max_y = self.y_glass - Y_BOUNDARY, self.y_glass + 2
        min_x, self.min_y, min_z = self.rotate((min_x, min_y, min_z))
        max_x, self.max_y, max_z = self.rotate((max_x, max_y, max_z))
        self.min_x, self.max_x = min(min_x, max_x), max(min_x, max_x)
        self.min_z, self.max_z = min(min_z, max_z), max(min_z, max_z)
        logger.info(
            "The structure will occupy the space "
            f"{(self.min_x, self.min_y, self.min_z)} "
            f"to {self.max_x, self.max_y, self.max_z} "
            f"in {self.world.dimension}"
        )
        if self.min_x < BOUNDS.min_x:
            raise UserError(
                f"Location is out of bound: x cannot go below {BOUNDS.min_x}"
            )
        if self.max_x > BOUNDS.max_x:
            raise UserError(
                f"Location is out of bound: x cannot go above {BOUNDS.max_x}"
            )
        if self.min_z < BOUNDS.min_z:
            raise UserError(
                f"Location is out of bound: z cannot go below {BOUNDS.min_z}"
            )
        if self.max_z > BOUNDS.max_z:
            raise UserError(
                f"Location is out of bound: z cannot go above {BOUNDS.max_z}"
            )
        if self.min_y < BOUNDS.min_y:
            raise UserError(
                f"Location is out of bound: y cannot go below {BOUNDS.min_y}"
            )
        if self.max_y > BOUNDS.max_y:
            raise UserError(
                f"Location is out of bound: y cannot go above {BOUNDS.max_y}"
            )

    def get_user_confirmation(self):
        if self.no_confirm:
            return
        return UserPrompt(
            prompt=("\nConfirm to proceed? [y/N] "),
            choices=("y", "yes"),
            blocking=False,
        )

    def prepare_space(self, Z: int):
        def generate_walking_glass():
            self[
                self.X + self.x_direction * x,
                self.y_glass,
                Z + self.z_direction * z,
            ] = GLASS
            for y in mandatory_clear_range:
                self[
                    self.X + self.x_direction * x,
                    y,
                    Z + self.z_direction * z,
                ] = AIR

        mandatory_clear_range = range(self.max_y, self.y_glass, -1)
        optional_clear_range = range(self.min_y, self.y_glass)

        def blend_block(coordinates: tuple[int, int, int], /) -> Optional[BlockType]:
            """Take coordinates to a block.
            Return what should be placed there in order to implement the blend feature.
            """

            block = self[coordinates]
            if (name := block.base_name) in REMOVE_LIST:
                return AIR
            if not isinstance(block, BlockType):
                return
            if block.extra_blocks:
                # remove all extra blocks, just in case water is among them
                return block.base_block
            try:
                if getattr(block, "waterlogged"):
                    return Block(name)
            except AttributeError:
                return

        for z in range(self.Z_BOUNDARY + 1):
            for x in range(self.X_BOUNDARY + 1):
                generate_walking_glass()
                for y in optional_clear_range:
                    coordinates = (
                        self.X + self.x_direction * x,
                        y,
                        Z + self.z_direction * z,
                    )
                    if (
                        not self.blend
                        or x in (0, self.X_BOUNDARY)
                        or z in (0, self.Z_BOUNDARY)
                    ):
                        self[coordinates] = AIR
                    else:
                        self[coordinates] = blend_block

    def generate_noteblocks(self, x: int, y: int, z: int, note: Note):
        # redstone components
        self[x, y, z] = self.theme_block
        self[x, y + 1, z] = self.Repeater(note.delay, self.z_direction)
        self[x, y + 1, z + self.z_direction] = self.theme_block
        self[x, y + 2, z + self.z_direction] = self.Redstone()
        self[x, y + 2, z + self.z_direction * 2] = self.theme_block

        # noteblocks
        if not note.dynamic:
            return

        noteblock = NoteBlock(note)
        for i in range(note.dynamic):
            self[x + self.noteblock_order[i], y + 2, z + self.z_direction] = noteblock
            if self.blend:
                self[x + self.noteblock_order[i], y + 1, z + self.z_direction] = AIR
                self[x + self.noteblock_order[i], y + 3, z + self.z_direction] = AIR

    def generate_division_bridge(self, x: int, y: int, z: int):
        self[x, y, z + self.z_direction * 2] = self.theme_block
        self[x, y + 1, z + self.z_direction * 2] = self.Redstone(
            self.z_direction, -self.z_direction
        )
        self[x, y, z + self.z_direction * 3] = self.theme_block
        self[x, y + 1, z + self.z_direction * 3] = self.Redstone(
            self.x_direction, -self.z_direction
        )
        for i in range(1, DIVISION_WIDTH):
            self[
                x + self.x_direction * i, y, z + self.z_direction * 3
            ] = self.theme_block
            self[
                x + self.x_direction * i, y + 1, z + self.z_direction * 3
            ] = self.Redstone(self.x_direction, -self.x_direction)
        self[
            x + self.x_direction * DIVISION_WIDTH, y, z + self.z_direction * 3
        ] = self.theme_block
        self[
            x + self.x_direction * DIVISION_WIDTH,
            y + 1,
            z + self.z_direction * 3,
        ] = self.Redstone(-self.z_direction, -self.x_direction)

    def generate_orchestra(self, voices: list[Voice], Z: int):
        if not voices:
            return

        self.prepare_space(Z)
        for i, voice in enumerate(voices[::-1]):
            y = self.y_glass - VOICE_HEIGHT * (i + 1) - 2
            z = Z + self.z_direction * (DIVISION_CHANGING_LENGTH + 2)
            for j, division in enumerate(voice):
                x = self.X + self.x_direction * (j * DIVISION_WIDTH + 3)
                z0 = z - self.z_direction * DIVISION_CHANGING_LENGTH
                self[x, y + 2, z0] = self.theme_block
                for k, note in enumerate(division):
                    z = z0 + k * self.z_direction * NOTE_LENGTH
                    self.generate_noteblocks(x, y, z, note)
                # if there is a next division, generate bridge and flip direction
                try:
                    voice[j + 1]
                except IndexError:
                    pass
                else:
                    self.generate_division_bridge(x, y, z)
                    self.z_direction = -self.z_direction
            # if number of division is even,
            # z_direction has been flipped, reset it to original
            if len(voice) % 2 == 0:
                self.z_direction = -self.z_direction

    def generate_init_system_for_single_orchestra(self, X: int):
        button = self.Button(face="floor", facing=-self.x_direction)
        redstone = self.Redstone(self.z_direction, -self.z_direction)

        x = self.X + self.x_direction * (X + math.ceil(DIVISION_WIDTH / 2))
        y = self.y_glass
        z = self.Z

        def the_first_one():
            def generate_button():
                """A button in the middle of the structure."""
                z_button = z + self.z_direction * math.ceil(self.Z_BOUNDARY / 2)
                self[x, y, z_button] = self.theme_block
                self[x, y + 1, z_button] = button

            def generate_redstone_bridge():
                """Connect the button to the main system."""
                repeater = self.Repeater(delay=1, direction=-self.z_direction)

                self[x, y - 3, z + self.z_direction] = self.theme_block
                self[x, y - 2, z + self.z_direction] = redstone
                self[x, y - 1, z + self.z_direction] = AIR
                self[x, y - 2, z + self.z_direction * 2] = self.theme_block
                self[x, y - 1, z + self.z_direction * 2] = redstone
                self[x, y - 1, z + self.z_direction * 3] = self.theme_block
                self[x, y, z + self.z_direction * 3] = redstone

                for i in range(4, math.ceil(self.Z_BOUNDARY / 2)):
                    self[x, y, z + self.z_direction * i] = self.theme_block
                    self[x, y + 1, z + self.z_direction * i] = (
                        redstone if i % 16 else repeater
                    )

            def generate_empty_bridge():
                """A bridge that leads to nowhere, just for symmetry."""
                for i in range(math.ceil(self.Z_BOUNDARY / 2) + 1, self.Z_BOUNDARY - 3):
                    self[x, y, z + self.z_direction * i] = self.theme_block

            generate_button()
            generate_redstone_bridge()
            generate_empty_bridge()

        def subsequent_ones():
            self[x, y - 3, z + self.z_direction] = self.theme_block
            self[x, y - 2, z + self.z_direction] = redstone
            self[x, y - 1, z + self.z_direction] = AIR
            self[x, y - 1, z + self.z_direction * 2] = redstone
            self[x, y - 1, z + self.z_direction * 3] = self.theme_block
            self[x, y, z + self.z_direction * 2] = self.theme_block
            self[x, y + 1, z + self.z_direction * 2] = button

        if X == 0:
            the_first_one()
        else:
            subsequent_ones()

    def generate_init_system_for_double_orchestras(self, X: int):
        def generate_bridge(z_direction: Direction):
            repeater = self.Repeater(delay=1, direction=-z_direction)
            self[x, y - 3, z + z_direction] = self.theme_block
            self[x, y - 2, z + z_direction] = redstone
            self[x, y - 1, z + z_direction] = AIR
            self[x, y - 2, z + z_direction * 2] = self.theme_block
            self[x, y - 1, z + z_direction * 2] = redstone
            self[x, y - 1, z + z_direction * 3] = self.theme_block
            self[x, y, z + z_direction * 3] = redstone

            for i in range(4, math.ceil(self.Z_BOUNDARY / 2) + 1):
                if X == 0 or i == 4:
                    self[x, y, z + z_direction * i] = self.theme_block
                self[x, y + 1, z + z_direction * i] = redstone if i % 16 else repeater

        def generate_button():
            z_button = z + self.z_direction * (math.ceil(self.Z_BOUNDARY / 2) + 1)
            button = self.Button(face="floor", facing=-self.x_direction)
            if X == 0 or self.composition.division == 1:
                self[x, y, z_button] = self.theme_block
            self[x, y + 1, z_button] = button

        redstone = self.Redstone(self.z_direction, -self.z_direction)
        x = self.X + self.x_direction * (X + math.ceil(DIVISION_WIDTH / 2))
        y = self.y_glass
        z = self.Z
        # button in the middle
        generate_button()
        # two redstone bridges going opposite directions,
        # connecting the button to each orchestra
        generate_bridge(self.z_direction)
        z += self.z_direction * (self.Z_BOUNDARY + 2)
        generate_bridge(-self.z_direction)

    def generate_composition(self):
        if len(self.composition) == 1:
            self.generate_orchestra(self.composition[0], self.Z)
        else:
            self.generate_orchestra(self.composition[0], self.Z)
            Z = self.Z + self.z_direction * self.Z_BOUNDARY
            self.generate_orchestra(self.composition[1], Z)

    def generate_init_system(self):
        if len(self.composition) == 1:
            for i in range(self.composition.length // 2):
                X = 2 * DIVISION_WIDTH * i
                self.generate_init_system_for_single_orchestra(X)
        else:
            for i in range(self.composition.length // 2):
                X = 2 * DIVISION_WIDTH * i
                self.generate_init_system_for_double_orchestras(X)
