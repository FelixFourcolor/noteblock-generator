# Minecraft noteblock generator

Generate a music composition in Minecraft noteblocks.

## Usage
```
python generate.py [path to music JSON file] [path to Minecraft world] [build coordinates]
```

Example: 
```
python generate.py my-composition.json My-World 0 0 0
```

If build coordinates are not provided, it will be the player's location.

See the JSON section for how to write the JSON file.

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
    
    "time": [how many steps in a bar],
    // If the time signature is 3/4, and we want to be able to play 16th notes,
    // the number of steps in a bar is 12.
    // Default value is 16, that is, 4/4 time and the ability to play 16th notes.
    // See the Generation section for how this value affects the build.

    "delay": [how many redstone ticks between each step],
    // Must be from 1 to 4, default value is 1.
    // For reference, if time is 16 and delay is 1, it is equivalent to quarter note = 150 bpm.
    
    "beat": [how many steps in a beat],
    // Does not affect the build, but is useful for writing notes (explained later).
    // Default value is 1.

    "instrument": [noteblock instrument to play the notes],
    // Default value is "harp".
    // See Minecraft's documentation for all available instruments.

    "dynamic": [how many noteblocks to play each note],
    // Must be from 0 to 4, where 0 is silent and 4 is loudest.
    // Warning: even with the same dynamic, some instruments are inherently louder than others.
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
            // you've made an error, e.g. invalid note name.

            "transpose": [transpose this particular voice, in semitones],
            // This value is compounded with the composition's transposition.
            // Default value is 0.

            "delay": [override the composition delay value],

            "beat": [override the composition beat value],

            "instrument": [override the composition instrument value],

            "dynamic": [override the composition dynamic value],

            "sustain": [override the composition sustain value],

            // Mandatory argument
            "notes":
            [
                // There are two ways to write notes.
                // First is as an object, like this:
                {
                    // Note 1

                    // Optional arguments

                    "transpose": [transpose this particular note, in semitones],
                    // This value is compounded with the voice's transposition. 
                    // Default value is 0.

                    "beat": [override the voice beat value],

                    "delay": [override the voice delay],

                    "dynamic": [override the voice dynamic],

                    "instrument": [override the voice instrument],

                    "sustain": [override the voice sustain value],

                    // (sort-of) Mandatory argument
                    // If a note object does not have the "name" value, it's not an actual note,
                    // but a syntactic sugar to apply the other key-value pairs
                    // to all subsequent notes in its voice.
                    // If a subsequent note defines its own values, some of which
                    // overlap with these values, the note's values take precedence.
                    "name": "[note name][octave] [duration]",

                    // Valid note names are "r" (rest) and "c", "cs", "db", etc.
                    // where "s" is for sharp and "b" is for flat. 
                    // Double sharps, double flats are supported. 
                    // No octave value for rests.

                    // Octaves range from 1 to 7.
                    // Warning: the lowest note noteblocks can play is F#1 and the highest is F#7, 
                    // so just because you can write it doesn't mean it will build
                    // (but you can transpose it to fit the range).
                    // Octave number can be inferred from the instrument's range.
                    // For example, using the harp whose range is F#3 - F#5, 
                    // "fs" is inferred as "fs 4", "fs^" as "fs 5", and "fs_" as "fs 3".
                    // See Minecraft's documentation for the range of each instrument.

                    // Duration is the number of steps. 
                    // For example, if a voice has 4/4 time and use time 8, 
                    // a quarter note has duration 2.
                    // If duration is omitted, it will be the beat number.
                    // If a duration number is followed by "b" (stands for "beats"),
                    // the number is multiplied by the beat number.
                    // Dotted rhythm is supported. If a duration value is followed by a ".",
                    // its value is multiplied by 1.5.
                    // If multiple values are given, they will be summed up, 
                    // for example, a note named "cs4 1 2 3" is the same as "cs4 6".
                    // Noteblocks cannot naturally sustain. If "sustain" is set to false (default), 
                    // a note with duration n is the same as the note with duration 1 and n-1 rests;
                    // otherwise, it's n repeated notes of duration 1.
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
                // 1) A pseudo-note named "|" asks the compiler to check if that position
                //    is the beginning of a bar and raise an error if it isn't.
                // 2) A note named "||" is to rest for the entire bar. That is,
                "||",
                //    is syntactic sugar for
                "|", "r [number of steps in a bar]",
                // 3) Both "|" and "||" can optionally be followed by a number, which asks
                //    the compiler to check if it's the correct bar number at that position
                //    and raise an error if it it isn't.
                //    For example, to rest for the first 4 bar and starts on bar 5:
                "||1", 
                "||2", 
                "||3", 
                "||4", 
                "| 5", "c", "d", "e", "c"
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
x
↑
| 
| [BAR 5] etc.
|          ↑
|          -- note <- note <- note [BAR 4]
|                               ↑
| [BAR 3] note -> note -> note --
|           ↑
|           - note <- note <- note [BAR 2]
|                               ↑
| [BAR 1] note -> note -> note --
|
O------------------------------------------> z
```
Each voice is a vertical layer on top of another. They are built in the order that they are written in the json file, from bottom to top.
Warning: noteblocks that are further away from the player sound softer; take this into account when choosing voice orders and/or dynamics.

The "O" of the first voice is considered the location of the build. The build coordinates mentioned in the Usage section are the coordinates of this location.

Each "note" in the above diagram is a group that looks like this:
```
x
↑
|            [noteblock]
|            [noteblock]
| [repeater]   [stone] 
|            [noteblock]
|            [noteblock]

|------------------------> z
```
The number of noteblocks depends on the note's dynamic level, this diagram shows one with maximum dynamic level 4.

Upon being called, the generator fills the required space starting from the build location with air, then generates the structure.

## License

Do whatever you want.
