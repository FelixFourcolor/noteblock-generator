def _generate_note_values() -> dict[str, int]:
    notes = ["c", "cs", "d", "ds", "e", "f", "fs", "g", "gs", "a", "as", "b"]
    octaves = {1: {note: value for value, note in enumerate(notes)}}
    for name, value in dict(octaves[1]).items():
        octaves[1][name + "s"] = value + 1
        if not name.endswith("s"):
            octaves[1][name + "b"] = value - 1
            octaves[1][name + "bb"] = value - 2
    for i in range(1, 7):
        octaves[i + 1] = {note: value + 12 for note, value in octaves[i].items()}
    return {note + str(octave): value for octave, notes in octaves.items() for note, value in notes.items()}


NOTE_VALUE = _generate_note_values()
INSTRUMENT_RANGE = {
    "basedrum": range(6, 31),
    "hat": range(6, 31),
    "snare": range(6, 31),
    "bass": range(6, 31),
    "didgeridoo": range(6, 31),
    "guitar": range(18, 43),
    "banjo": range(30, 55),
    "bit": range(30, 55),
    "harp": range(30, 55),
    "iron_xylophone": range(30, 55),
    "pling": range(30, 55),
    "cow_bell": range(42, 67),
    "flute": range(42, 67),
    "bell": range(54, 79),
    "xylophone": range(54, 79),
    "chime": range(54, 79),
}
