import amulet as _amulet

_version = ("java", (1, 20))


class Block(_amulet.api.block.Block):
    """A wrapper for amulet Block,
    with more convenient constructor."""

    def __init__(self, name: str, properties: dict[str, int | str]):
        _properties = {k: _amulet.StringTag(v) for k, v in properties.items()}
        super().__init__("minecraft", name, _properties)


class World:
    """A wrapper for amulet BaseLevel,
    with more convenient method arguments
    and context manager to auto-save."""

    def __init__(self, path: str):
        self._path = path

    def __enter__(self):
        self._level = _amulet.load_level(self._path)
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if self._level.changed:
            self._level.save()
        self._level.close()

    def set_block(self, x: int, y: int, z: int, block: Block):
        self._level.set_version_block(x, y, z, "minecraft:overworld", _version, block)


world = World("World")
