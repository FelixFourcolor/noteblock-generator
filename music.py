# mapping of pitch names to their values
_octaves = [
    # create the first octave
    ["fs1", "g1", "gs1", "a1", "as1", "b1", "c2", "cs2", "d2", "ds2", "e2", "f2"]
]
for _ in range(5):
    # dynamically extend to octave 7
    _octaves.append([p[:-1] + str(int(p[-1]) + 1) for p in _octaves[-1]])
_PITCHES = {
    # flatten and convert to dict
    name: value
    for value, name in enumerate(
        [pitch for octave in _octaves for pitch in octave] + ["fs7"]
    )
}
for name, value in dict(_PITCHES).items():
    # extend accidentals
    if name[-2] == "s":
        # double sharps
        if value + 1 <= 72:
            _PITCHES[name[:-1] + "s" + name[-1]] = value + 1
            _PITCHES[name[:-2] + "x" + name[-1]] = value + 1
    else:
        # flats
        if value - 1 >= 0:
            _PITCHES[name[:-1] + "b" + name[-1]] = value - 1
        # double flats
        if value - 2 >= 0:
            _PITCHES[name[:-1] + "bb" + name[-1]] = value - 2

# Mapping of instruments to their ranges
_INSTRUMENTS = {
    "bass": range(0, 24),
    "didgeridoo": range(0, 24),
    "guitar": range(12, 36),
    "harp": range(24, 48),
    "bit": range(24, 48),
    "banjo": range(24, 48),
    "iron_xylophone": range(24, 48),
    "pling": range(24, 48),
    "flute": range(36, 60),
    "cow_bell": range(36, 60),
    "bell": range(48, 72),
    "xylophone": range(48, 72),
    "chime": range(48, 72),
    "basedrum": range(72),
    "hat": range(72),
    "snare": range(72),
}
