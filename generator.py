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
                facing = "south"
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


# TODO
def generate(composition: Composition, path: str):
    print(composition)
    for voice in composition:
        print(voice)
        for i, bar in enumerate(voice):
            print(i + 1, bar)
