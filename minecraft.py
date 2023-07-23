import amulet as _amulet

from music import Composition

_namespace = "minecraft:overworld"
_version = ("java", (1, 20))


class Block(_amulet.api.block.Block):
    """A wrapper for amulet Block,
    with a more convenient constructor.
    """

    def __init__(self, name: str, **properties):
        # WARNING: there is no error message if 'name' is not a valid block name
        properties = {k: _amulet.StringTag(v) for k, v in properties.items()}
        super().__init__("minecraft", name, properties)


class World:
    """A wrapper for amulet.load_level,
    with some conveniece methods to edit world and a context manager to auto-save.
    """

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
