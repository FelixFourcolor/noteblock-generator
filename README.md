# Noteblock generator

Generate a music composition in Minecraft noteblocks

## Usage
```
generate.py [-h] [-l [LOCATION ...]] [-o [ORIENTATION ...]] [-b BLOCK] [--clear] path_in path_out

positional arguments:
  path_in               path to music json file
  path_out              path to Minecraft world

options:
  -h, --help            show this help message and exit
  -l [LOCATION ...], --location [LOCATION ...]
                        generate location (in x y z); default is ~ ~ ~ (player's location)
  -o [ORIENTATION ...], --orientation [ORIENTATION ...]
                        in which directions (in x y z) to generate; default is + + +
  -b BLOCK, --block BLOCK
                        what to use as opaque blocks for redstone components; default is stone
  --clear               clear the space before generating;
                        required to generate in a non-empty world but will take more time
```

See the JSON section for how to write a music JSON file.

See the Generation section for what the generated structure will look like.

## Dependencies
* python 3.10+

* [Amulet-Core](https://github.com/Amulet-Team/Amulet-Core)

## JSON

The user writes a JSON file that specifies a music composition. The file should be in this format:
```json5
{
    // Composition

    // Optional arguments
    
    "time": [how many redstone units in a bar],
    // A redstone unit is the shortest unit of time in a composition.
    // This value controls both the fastest playable note and the composition's time signature.
    // For example, if the time signature is 3/4, and we want to play 16th notes,
    // the required number of units in a bar is 12.
    // Default value is 16, that is, 4/4 time and the ability to play 16th notes.

    "delay": [how many redstone ticks for each redstone unit],
    // One redstone tick = 0.1s. This value effectively controls the tempo.
    // For example, if time is 16 and delay is 1 (defaults), it's the tempo quarter note=150 bpm.
    // Must be from 1 to 4. Default value is 1.
    
    "beat": [how many redstone units in a beat],
    // Does not affect the build, but is useful for writing notes (explained later).
    // Default value is 1.

    "instrument": [noteblock instrument to play the notes],
    // See Minecraft's documentation for all available instruments.
    // Default value is "harp".

    "dynamic": [how many noteblocks to play each note],
    // Must be from 0 to 4, where 0 is silent and 4 is loudest.
    // Default value is 2.

    "transpose": [transpose the entire composition, in semitones],
    // Default value is 0.

    "sustain": [whether to sustain the notes],
    // Noteblocks cannot naturally sustain. 
    // If set to true, the notes will fake sustain with tremolo.
    // Default value is false.

    // Mandatory argument
    "voices":
    [
        {
            // Voice 1

            // Optional arguments

            "name": [voice name],
            // Does not affect the build, but is useful for error messages, which,
            // if voice name is given, will tell you at which voice 
            // you have made an error, e.g. invalid note name.

            "transpose": [transpose this voice, in semitones],
            // This value is compounded with the composition's transposition.
            // Default value is 0.

            "delay": [override the composition delay for this voice],

            "beat": [override the composition beat for this voice],

            "instrument": [override the composition instrument for this voice],

            "dynamic": [override the composition dynamic for this voice],

            "sustain": [override the composition sustain for this voice],

            // Mandatory argument
            "notes":
            [
                // There are two ways to write notes.
                // First is as an object, like this:
                {
                    // Note 1

                    // Optional arguments

                    "transpose": [transpose this note, in semitones],
                    // This value is compounded with the voice's transposition.
                    // Default value is 0.

                    "beat": [override the voice beat for this note],

                    "delay": [override the voice delay for this note],

                    "dynamic": [override the voice dynamic for this note],

                    "instrument": [override the voice instrument for this note],

                    "sustain": [override the voice sustain for this note],

                    // (sort-of) Mandatory argument
                    // If a note object does not have the "name" value, it's not an actual note,
                    // but a syntactic sugar to apply the other key-value pairs
                    // to all subsequent notes in this voice.
                    // If a subsequent note defines its own values, some of which
                    // overlap with these values, the note's values take precedence.
                    "name": "[note name][octave] [duration]",

                    // Valid note names are "r" (rest) and "c", "cs", "db", etc.
                    // where "s" is for sharp and "b" is for flat. 
                    // Double sharps, double flats are supported. 
                    // No octave value for rests.

                    // Valid octaves are 1 to 7.
                    // Octave number can be inferred from the instrument's range.
                    // For example, using the harp whose range is F#3 - F#5, 
                    // "fs" is inferred as "fs 4", "fs^" as "fs 5", and "fs_" as "fs 3".
                    // See Minecraft's documentation for the range of each instrument.

                    // Duration is the number of redstone units. 
                    // For example, if a voice has 4/4 time and use time 8, 
                    // a quarter note has duration 2.
                    // If duration is omitted, it will be the beat number.
                    // If a duration number is followed by "b" (stands for "beats"),
                    // the number is multiplied by the beat number.
                    // Dotted rhythm is supported. If a duration value is followed by a ".",
                    // its value is multiplied by 1.5.
                    // If multiple values are given, they will be summed up, 
                    // for example, a note named "cs4 1 2 3" is the same as "cs4 6".
                    // If sustain is false (default), a note with duration n
                    // is the same as the note with duration 1 and n-1 rests;
                    // otherwise, it is n repeated notes of duration 1.
                },

                {
                    // Note 2
                    // etc.
                },

                // Note 3, etc.

                // Another way is to write it as a string, like this:
                "[note name][octave] [duration]",
                // which is syntactic sugar for
                {
                    // omit all optional arguments
                    "name": "[note name][octave] [duration]"
                },

                // Notes are automatically divided into bars based on composition's time,
                // no user action is needed. However, the user may find these helpers useful:
                // 1) A pseudo-note named "|" is to assert a barline. The compiler will check if
                //    a barline is appropriate at that position, and raise and error if it's not.
                // 2) A note named "||" is to rest for the entire bar. It's a syntactic sugar for
                "|", "r [number of units in a bar]",
                // 3) Both "|" and "||" can optionally be followed by a number, which asserts bar number.
                //    The compiler will check if it's the correct bar number at that position
                //    and raise an error if it it isn't.
                //    For example, to rest for the first 2 bar and start on bar 3:
                "||1", 
                "||2", 
                "| 3", "c", "d", "e", "c"
            ]
        },
        
        {
            // Voice 2
            // etc.
        }
        
        // Voice 3, etc.
    ]
}
```
See "example.json" which writes the Frere Jacques round in C major for 3 voices. And see "World" for the build result.

## Generation
The generated structure of one voice looks like this:
```
x (+/-)
↑
| 
| [BAR 5] etc.
|          ↑
|          -- unit <- unit <- unit [BAR 4]
|                               ↑
| [BAR 3] unit -> unit -> unit --
|           ↑
|           - unit <- unit <- unit [BAR 2]
|                               ↑
| [BAR 1] unit -> unit -> unit --
|
O------------------------------------------> z (+/-)
```
A "unit" refers to a redstone unit mentioned in the JSON section.

The x-axis goes + or - depends on the x-orientation mentioned in the Usage section. And similarly with the z-axis.

Each voice is a vertical layer on top of another. They are built in the order that they are written in the json file. They go from bottom to top (+) or top to bottom (-) depending on the y-orientation.

The "O" of the first voice is the generate location mentioned in the Usage section.

Each redstone unit is a group that looks like this:
```
x (+/-)
↑
|            [noteblock]
|            [noteblock]
| [repeater]   [block] 
|            [noteblock]
|            [noteblock]

|------------------------> z (+/-)
```

A "block" refers to the opaque block mentioned in the Usage section.

The number of noteblocks depends on the note's dynamic value mentioned in the JSON section, this diagram shows one with maximum value 4.

## License

Do whatever you want.
