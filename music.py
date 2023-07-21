# MAPPING OF PITCH NAMES TO NUMERICAL VALUES
# create first octave
_first = ["c1", "cs1", "d1", "ds1", "e1", "f1", "fs1", "g1", "gs1", "a1", "as1", "b1"]
_octaves = [_first]
# dynamically extend to octave 7
for _ in range(6):
    _octaves.append([p[:-1] + str(int(p[-1]) + 1) for p in _octaves[-1]])
# flatten and convert to dict
PITCHES = {
    name: value
    for value, name in enumerate([pitch for octave in _octaves for pitch in octave])
}
# extend accidentals
for name, value in dict(PITCHES).items():
    if name[-2] == "s":
        # double sharps
        if value + 1 < 84:
            PITCHES[name[:-1] + "s" + name[-1]] = value + 1
            PITCHES[name[:-2] + "x" + name[-1]] = value + 1
    else:
        # flats
        if value - 1 >= 0:
            PITCHES[name[:-1] + "b" + name[-1]] = value - 1
        # double flats
        if value - 2 >= 0:
            PITCHES[name[:-1] + "bb" + name[-1]] = value - 2

# MAPPING OF INSTRUMENTS TO NUMERICAL RANGES
INSTRUMENTS = {
    "bass": range(6, 30),
    "didgeridoo": range(6, 30),
    "guitar": range(18, 42),
    "harp": range(30, 54),
    "bit": range(30, 54),
    "banjo": range(30, 54),
    "iron_xylophone": range(30, 54),
    "pling": range(30, 54),
    "flute": range(42, 66),
    "cow_bell": range(42, 66),
    "bell": range(54, 78),
    "xylophone": range(54, 78),
    "chime": range(54, 78),
    "basedrum": range(78),
    "hat": range(78),
    "snare": range(78),
}
