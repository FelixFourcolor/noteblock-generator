import math
from dataclasses import dataclass
from typing import Optional

from .main import Location, Orientation, logger
from .parser import Composition, Rest, UserError, Voice
from .world import (
    Block,
    Direction,
    NoteBlock,
    Redstone,
    Repeater,
    UserPrompt,
    World,
    _BlockType,
    progress_bar,
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
            self._generate()

    def _generate(self):
        # -----------------------------------------------------------------------------
        # Subroutines

        def generate_init_system_for_single_orchestra(x0: int):
            button = Block("oak_button", face="floor", facing=-x_direction)
            redstone = Redstone(z_direction, -z_direction)

            x = X + x_direction * (x0 + math.ceil(DIVISION_WIDTH / 2))
            y = y_glass
            z = Z

            def first():
                def generate_button():
                    """A button in the middle of the structure."""
                    z_button = z + z_direction * math.ceil(Z_BOUNDARY / 2)
                    self.world[x, y, z_button] = theme_block
                    self.world[x, y + 1, z_button] = button

                def generate_redstone_bridge():
                    """Connect the button to the main system."""
                    repeater = Repeater(delay=1, direction=-z_direction)

                    self.world[x, y - 3, z + z_direction] = theme_block
                    self.world[x, y - 2, z + z_direction] = redstone
                    self.world[x, y - 1, z + z_direction] = air
                    self.world[x, y - 2, z + z_direction * 2] = theme_block
                    self.world[x, y - 1, z + z_direction * 2] = redstone
                    self.world[x, y - 1, z + z_direction * 3] = theme_block
                    self.world[x, y, z + z_direction * 3] = redstone

                    for i in range(4, math.ceil(Z_BOUNDARY / 2)):
                        self.world[x, y, z + z_direction * i] = theme_block
                        self.world[x, y + 1, z + z_direction * i] = (
                            redstone if i % 16 else repeater
                        )

                def generate_empty_bridge():
                    """A bridge that leads to nowhere, just for symmetry."""
                    for i in range(math.ceil(Z_BOUNDARY / 2) + 1, Z_BOUNDARY - 3):
                        self.world[x, y, z + z_direction * i] = theme_block

                generate_button()
                generate_redstone_bridge()
                generate_empty_bridge()

            def subsequent():
                self.world[x, y - 3, z + z_direction] = theme_block
                self.world[x, y - 2, z + z_direction] = redstone
                self.world[x, y - 1, z + z_direction] = air
                self.world[x, y - 1, z + z_direction * 2] = redstone
                self.world[x, y - 1, z + z_direction * 3] = theme_block

                self.world[x, y, z + z_direction * 2] = theme_block
                self.world[x, y + 1, z + z_direction * 2] = button

            if x0 == 0:
                first()
            else:
                subsequent()

        def generate_init_system_for_double_orchestras(x0: int):
            def generate_bridge(z: int, z_direction: Direction):
                repeater = Repeater(delay=1, direction=-z_direction)
                self.world[x, y - 3, z + z_direction] = theme_block
                self.world[x, y - 2, z + z_direction] = redstone
                self.world[x, y - 1, z + z_direction] = air
                self.world[x, y - 2, z + z_direction * 2] = theme_block
                self.world[x, y - 1, z + z_direction * 2] = redstone
                self.world[x, y - 1, z + z_direction * 3] = theme_block
                self.world[x, y, z + z_direction * 3] = redstone

                for i in range(4, math.ceil(Z_BOUNDARY / 2) + 1):
                    if x0 == 0 or i == 4:
                        self.world[x, y, z + z_direction * i] = theme_block
                    self.world[x, y + 1, z + z_direction * i] = (
                        redstone if i % 16 else repeater
                    )

            def generate_button():
                z = Z + z_direction * (1 - math.ceil(Z_BOUNDARY / 2))
                button = Block("oak_button", face="floor", facing=-x_direction)
                if x0 == 0 or self.composition.division == 1:
                    self.world[x, y, z] = theme_block
                self.world[x, y + 1, z] = button

            x = X + x_direction * (x0 + math.ceil(DIVISION_WIDTH / 2))
            y = y_glass
            redstone = Redstone(z_direction, -z_direction)

            generate_bridge(Z - z_direction * Z_BOUNDARY, z_direction)
            generate_bridge(Z + z_direction * 2, -z_direction)
            generate_button()

        def generate_orchestra(voices: list[Voice], z_direction: Direction):
            if not voices:
                return

            def generate_space():
                def generate_walking_glass():
                    self.world[
                        X + x_direction * x, y_glass, Z + z_direction * z
                    ] = glass
                    for y in mandatory_clear_range:
                        self.world[
                            X + x_direction * x,
                            y,
                            Z + z_direction * z,
                        ] = air

                glass = Block("glass")

                mandatory_clear_range = range(max_y, y_glass, -1)
                optional_clear_range = range(min_y, y_glass)

                def blend_block(xyz: tuple[int, int, int], /) -> Optional[_BlockType]:
                    """Take coordinates to a block.
                    Return what should be placed there in order to implement the self.blend feature.
                    """

                    block = self.world[xyz]
                    if (name := block.base_name) in REMOVE_LIST:
                        return air
                    if not isinstance(block, _BlockType):
                        return
                    if block.extra_blocks:
                        # remove all extra blocks, just in case water is among them
                        return block.base_block
                    try:
                        if getattr(block, "waterlogged"):
                            return Block(name)
                    except AttributeError:
                        return

                for z in range(Z_BOUNDARY + 1):
                    for x in range(X_BOUNDARY + 1):
                        generate_walking_glass()
                        for y in optional_clear_range:
                            coordinates = (
                                X + x_direction * x,
                                y,
                                Z + z_direction * z,
                            )
                            if (
                                not self.blend
                                or x in (0, X_BOUNDARY)
                                or z in (0, Z_BOUNDARY)
                            ):
                                self.world[coordinates] = air
                            else:
                                self.world[coordinates] = blend_block

            def generate_redstones():
                self.world[x, y, z] = theme_block
                self.world[x, y + 1, z] = Repeater(note.delay, z_direction)
                self.world[x, y + 1, z + z_direction] = theme_block
                self.world[x, y + 2, z + z_direction] = Redstone()
                self.world[x, y + 2, z + z_direction * 2] = theme_block

            def generate_noteblocks():
                if not note.dynamic:
                    return

                placement_order = [
                    -x_direction,
                    x_direction,
                    -x_direction * 2,
                    x_direction * 2,
                ]

                noteblock = NoteBlock(note)
                for i in range(note.dynamic):
                    self.world[
                        x + placement_order[i], y + 2, z + z_direction
                    ] = noteblock
                    if self.blend:
                        self.world[x + placement_order[i], y + 1, z + z_direction] = air
                        self.world[x + placement_order[i], y + 3, z + z_direction] = air

            def generate_division_bridge():
                self.world[x, y, z + z_direction * 2] = theme_block
                self.world[x, y + 1, z + z_direction * 2] = Redstone(
                    z_direction, -z_direction
                )
                self.world[x, y, z + z_direction * 3] = theme_block
                self.world[x, y + 1, z + z_direction * 3] = Redstone(
                    x_direction, -z_direction
                )
                for i in range(1, DIVISION_WIDTH):
                    self.world[
                        x + x_direction * i, y, z + z_direction * 3
                    ] = theme_block
                    self.world[
                        x + x_direction * i, y + 1, z + z_direction * 3
                    ] = Redstone(x_direction, -x_direction)
                self.world[
                    x + x_direction * DIVISION_WIDTH, y, z + z_direction * 3
                ] = theme_block
                self.world[
                    x + x_direction * DIVISION_WIDTH, y + 1, z + z_direction * 3
                ] = Redstone(-z_direction, -x_direction)

            generate_space()

            for i, voice in enumerate(voices[::-1]):
                for _ in range(INIT_DIVISIONS):
                    voice.insert(0, [Rest(voice, delay=1)] * voice.division)

                y = y_glass - VOICE_HEIGHT * (i + 1) - 2
                z = Z + z_direction * (DIVISION_CHANGING_LENGTH + 2)

                for j, division in enumerate(voice):
                    x = X + x_direction * (1 + DIVISION_WIDTH // 2 + j * DIVISION_WIDTH)
                    z0 = z - z_direction * DIVISION_CHANGING_LENGTH
                    self.world[x, y + 2, z0] = theme_block

                    for k, note in enumerate(division):
                        z = z0 + k * z_direction * NOTE_LENGTH
                        generate_redstones()
                        generate_noteblocks()

                    # if there is a next division, change division and flip direction
                    try:
                        voice[j + 1]
                    except IndexError:
                        pass
                    else:
                        generate_division_bridge()
                        z_direction = -z_direction

                # if number of division is even
                if len(voice) % 2 == 0:
                    # z_direction has been flipped, reset it to original
                    z_direction = -z_direction

        # Function main begins
        # -----------------------------------------------------------------------------
        # Parse arguments

        NOTE_LENGTH = 2  # noteblock + repeater
        DIVISION_WIDTH = 5  # 4 noteblocks (maximum dynamic range) + 1 stone
        VOICE_HEIGHT = 2  # noteblock + air above
        DIVISION_CHANGING_LENGTH = 2  # how many blocks it takes to wrap around each bar
        INIT_DIVISIONS = math.ceil(
            (self.composition.size - 1) / self.composition.division
        )
        # this number of divisions is added to the beginning of every voice
        # so that with a push of a button, all voices start at the same time

        air = Block("air")
        theme_block = Block(self.theme)

        X, Y, Z = self.location
        if self.location.x.relative:
            X += int(self.world.player_location[0])
        if self.location.y.relative:
            Y += int(self.world.player_location[1])
        if self.location.z.relative:
            Z += int(self.world.player_location[2])
        if self.dimension is None:
            self.dimension = self.world.player_dimension
        if self.dimension not in self.world.dimensions:
            raise UserError(
                f"{self.dimension} is not a valid self.dimension; expected one of {self.world.dimensions}"
            )
        self.world.dimension = self.dimension

        x_direction = Direction.east
        if not self.orientation.x:
            x_direction = -x_direction
        if self.orientation.y:
            y_glass = Y + VOICE_HEIGHT * (self.composition.size + 1)
        else:
            y_glass = Y - 1
        z_direction = Direction.south
        if not self.orientation.z:
            z_direction = -z_direction

        # -----------------------------------------------------------------------------
        # Calculate the space the structure will occucpy,
        # and verify that it's within bounds

        X_BOUNDARY = (self.composition.length + INIT_DIVISIONS) * DIVISION_WIDTH + 1
        Z_BOUNDARY = (
            self.composition.division * NOTE_LENGTH + DIVISION_CHANGING_LENGTH + 2
        )
        Y_BOUNDARY = VOICE_HEIGHT * (self.composition.size + 1)
        BOUNDS = self.world.bounds

        if self.orientation.x:
            min_x, max_x = X, X + X_BOUNDARY
        else:
            min_x, max_x = X - X_BOUNDARY, X
        if min_x < BOUNDS.min_x:
            raise UserError(
                f"Location is out of bound: x-coordinate cannot go below {BOUNDS.min_x}"
            )
        if max_x > BOUNDS.max_x:
            raise UserError(
                f"Location is out of bound: x-coordinate cannot go above {BOUNDS.max_x}"
            )

        if self.orientation.z:
            min_z = Z
            if len(self.composition) == 1:
                max_z = Z + Z_BOUNDARY
            else:
                max_z = Z + 2 * Z_BOUNDARY
        else:
            max_z = Z
            if len(self.composition) == 1:
                min_z = Z - Z_BOUNDARY
            else:
                min_z = Z - 2 * Z_BOUNDARY
        if min_z < BOUNDS.min_z:
            raise UserError(
                f"Location is out of bound: z-coordinate cannot go below {BOUNDS.min_z}"
            )
        if max_z > BOUNDS.max_z:
            raise UserError(
                f"Location is out of bound: z-coordinate cannot go above {BOUNDS.max_z}"
            )

        min_y, max_y = y_glass - Y_BOUNDARY, y_glass + 2
        if min_y < BOUNDS.min_y:
            raise UserError(
                f"Location is out of bound: y-coordinate cannot go below {BOUNDS.min_y}"
            )
        if max_y > BOUNDS.max_y:
            raise UserError(
                f"Location is out of bound: y-coordinate cannot go above {BOUNDS.max_y}"
            )

        # -----------------------------------------------------------------------------
        # Get user confirmation

        if self.no_confirm:
            user_prompt = None
        else:
            dimension = self.dimension
            if dimension.startswith("minecraft:"):
                dimension = self.dimension[10:]
            user_prompt = UserPrompt(
                prompt=(
                    "\nThe structure will occupy the space "
                    f"{(min_x, min_y, min_z)} to {max_x, max_y, max_z} in {dimension}."
                    "\nConfirm to proceed? [Y/n] "
                ),
                choices=("", "y", "yes"),
                blocking=False,  # start generating while waiting for user input, just don't save yet.
            )

        # -----------------------------------------------------------------------------
        # Generate

        try:
            progress_bar(0, 1, text="Generating")

            if len(self.composition) == 1:
                generate_orchestra(self.composition[0], z_direction)
                for i in range(self.composition.length // 2):
                    generate_init_system_for_single_orchestra(2 * DIVISION_WIDTH * i)
            else:
                generate_orchestra(self.composition[0], z_direction)
                Z += z_direction * Z_BOUNDARY
                generate_orchestra(self.composition[1], z_direction)
                for i in range(self.composition.length // 2):
                    generate_init_system_for_double_orchestras(2 * DIVISION_WIDTH * i)
            self.world.apply_modifications()

            # Wait for user confirmation, then save
            if user_prompt is not None:
                user_prompt.wait()
            modified_by_another_process = self.world.save()

        except KeyboardInterrupt:
            # If user denies, KeyboardInterrupt will be raised, which is caught here
            print()
            logger.info("Aborted.")
        else:
            logger.info("Finished.")
            if modified_by_another_process:
                logger.info(
                    "If you are currently inside the world, exit and re-enter to see result."
                )
