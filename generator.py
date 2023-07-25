import amulet as _amulet

from music import INSTRUMENTS, Composition

_namespace = "minecraft:overworld"
_version = ("java", (1, 20))


class Block(_amulet.api.block.Block):
    def __init__(self, name: str, **properties):
        properties = {k: _amulet.StringTag(v) for k, v in properties.items()}
        super().__init__("minecraft", name, properties)


class NoteBlock(Block):
    def __init__(self, note: int, instrument="harp"):
        if note not in range(25):
            raise ValueError("note must be in range(25).")
        if instrument not in INSTRUMENTS:
            raise ValueError(f"{instrument} is not a valid instrument.")
        super().__init__("note_block", note=note, instrument=instrument)


class Repeater(Block):
    def __init__(self, delay: int, direction: tuple[int, int]):
        if delay not in range(1, 5):
            raise ValueError("delay must be in range(1, 5).")
        match direction:
            case (0, 1):
                facing = "north"
            case (0, -1):
                facing = "south"
            case (1, 0):
                facing = "west"
            case (-1, 0):
                facing = "east"
            case _:
                raise ValueError("Invalid direction.")
        super().__init__("repeater", delay=delay, facing=facing)


class World:
    def __init__(self, path: str):
        self._path = path

    def __enter__(self):
        self._level = _amulet.load_level(self._path)
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if self._level.changed:
            self._level.save()
        self._level.close()

    def __getitem__(self, coordinates: tuple[int, int, int]):
        return self._level.get_version_block(*coordinates, _namespace, _version)

    def __setitem__(self, coordinates: tuple[int, int, int], block: Block | str):
        if isinstance(_block := block, str):
            _block = Block(_block)
        self._level.set_version_block(*coordinates, _namespace, _version, _block)


def generate(composition: Composition, path: str):
    def generate_skeleton():
        world[x, y, z] = Repeater(note.delay, (0, z_vector))
        world[x, y + 1, z] = Stone
        world[x, y, z + z_vector] = Stone

    def generate_notes():
        noteblock_order = [1, -1, 2, -2]
        world[x, y + 1, z + z_vector] = Redstone
        for k in range(note.dynamic):
            x_i = x + noteblock_order[k]
            world[x_i, y + 1, z + z_vector] = NoteBlock(note.note, note.instrument)

    def generate_bar_change():
        bridge = [
            (0, z_vector * 2),
            (0, z_vector * 3),
            (1, z_vector * 3),
            (2, z_vector * 3),
            (3, z_vector * 3),
            (4, z_vector * 3),
            (5, z_vector * 3),
        ]
        for X, Z in bridge:
            world[x + X, y, z + Z] = Redstone

    Redstone = Block("redstone_wire")
    Stone = Block("stone")
    with World(path) as world:
        for i, voice in enumerate(composition):
            y = 2 * i  # each voice takes 2 blocks of height
            for j, bar in enumerate(voice):
                x = 5 * j  # each bar takes 5 blocks of width
                if j % 2:  # build direction alternates each bar
                    z_vector = 1
                    z = 0
                else:
                    z_vector = -1
                    z = 2 * len(bar)
                for note in bar:
                    z += 2 * z_vector  # each note takes 2 blocks of length
                    generate_skeleton()
                    generate_notes()
                generate_bar_change()
