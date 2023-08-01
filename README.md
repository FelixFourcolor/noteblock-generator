# Minecraft noteblock generator

Generate a music composition in minecraft noteblocks.

## Usage
```
python generate.py [path to music JSON file] [path to minecraft world] [(optional) build coordinates]
```

Example: 
```
python generate.py my-composition.json My-World 0 0 0
```

If build coordinates are not provided, it will be the player's location.

See the JSON section for how to write the JSON file.

See the Generation section for what the generated structure will look like.

## Dependencies
python 3.10+

amulet-core, available on PyPI

## JSON

The user writes a JSON file that specifies a music composition. This file is first translated into python objects, then generated in minecraft noteblocks.

The JSON file should be in this format:
```json5
{
    // Composition

    // Optional arguments
    "time": [how many steps in a bar],
    // If the time signature is 3/4, and we want to be able to play 16th notes,
    // the number of steps in a bar is 12.
    // Default value is 16, that is, 4/4 time and the ability to play 16th notes.
    // See Generation section for how this value affects the build.
    "delay": [how many redstone ticks between each step],
    // Must be from 1 to 4, default value is 1.
    // For reference, if time is 16 and delay is 1, it is equivalent to 
    // the tempo "quarter note = 150 bpm"
    "beat": [how many steps in a beat],
    // Does not affect the build, but is useful for writing notes (explained later).
    // Default value is 1.
    "instrument": "[noteblock instrument to play the notes]",
    // Default value is "harp".
    // See minecraft's documentations for all available instruments.
    "dynamic": [how many noteblocks to play the note],
    // Must be from 0 to 4, where 0 is silent and 4 is loudest.
    // Default value is 2.
    "transpose": [transpose the entire composition, in semitones],
    // Default value is 0.

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
            //Default value is 0.
            "time": [override the composition time],
            "delay": [override the composition delay],
            "beat": [override the composition beat],
            "instrument": "[override the composition's instrument]",
            "dynamic": [override the composition dynamic],
            // Some instruments are inherently louder than others, 
            // it is recommened to adjust the dynamic level of every voice 
            // to compensate for this fact.
            
            // Mandatory argument
            "notes":
            [
                // There are two ways to write notes.
                // First is as an object, like this
                {
                    // Note 1

                    // Optional arguments
                    "transpose": [transpose this particular note, in semitones],
                    // This value is compounded with the voice's transposition. 
                    // Default value is 0.
                    "delay": [override the voice delay],
                    "dynamic": [override the voice dynamic],
                    "instrument": "[override the voice's instrument]",

                    // (sort-of) Mandatory argument
                    "name": "[note name][octave] [duration 1] [duration 2] [etc.]"

                    // Valid note names are "r" (rest) and "c", "cs", "db", etc.
                    // where "s" is for sharp and "b" is for flat. 
                    // Double sharps, double flats are supported. 
                    // No octave value for rests.

                    // Octaves range from 1 to 7. Note, however, that the 
                    // lowest note noteblocks can play is F#1 and the highest is F#7, 
                    // so just because you can write it doesn't mean it will build 
                    //(but you can transpose it to fit the range).
                    // Octave number can be inferred from the instrument's range.
                    // For example, using the harp whose range is F#3 - F#5, 
                    // "fs" is inferred as "fs 4", "fs^" as "fs 5", and "fs_" as "fs 3".
                    // See minecraft's documentation for the range of each instrument.

                    // Duration is the number of steps. For example, if a voice has 
                    // 4/4 time and use time 8, a quarter note has duration 2.
                    // If duration is omitted, it will be the beat number.
                    // If multiple durations are given, they will be summed up, 
                    // for example, note name "cs4 1 2 3" is the same as "cs4 6".
                    // Because noteblocks cannot sustain, a note with duration n 
                    // is the same as the note with duration 1 and n-1 rests. 
                    // However, for readability, it is recommended to write notes 
                    // as they are written in the score.

                    // Syntactic sugar:
                    // 1) The note name "||" is short for "rest for the remaining
                    //    of the current bar."
                    // 2) If a note object does not have the "name" value, the other
                    //    key-value pairs will be applied to all subsequent in its voice.
                    //    If a subsequent note defines its own values, some of which
                    //    overlap with these values, the note's values take precedence.
                },

                {
                    // Note 2
                    // etc.
                },

                // Note 3, etc.

                // Another way is to write it as a string, 
                // which is the same as { "name": "that string" }.

                // Bar changes are handled automatically based on the voice's time. 
                // However, the recommended practice is to write a pseudo-note 
                // "| [bar number]" at the beginning of every bar. 
                // The "|" note tells the translator to check if it's indeed 
                // the beginning of a bar, and raise an error if it isn't. 
                // Meanwhile, the bar number is just for your own reference.
            ]
        },
        
        {
            // Voice 2
            // etc.
        },
        
        // Voice 3, etc.
    ]
}
```
For an example, see "frere jacques.json", which writes the Frere Jacques round in C major for 5 voices. And see the "Frere Jacques" world for the build result.

## Generation
The generated structure of one voice looks something like this
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
Each voice is a vertical layer on top of another. They are built in the order that they are written in the json file, from bottom to top. It is recommended to give lower voices higher dynamic levels to compensate for the fact that being further away from the player who flies above, they are harder to hear.

The "O" of the first voice is considered the location of the build.
The build coordinates mentioned in the Usage section are the coordinates of this location.

Each "note" in the above diagram is a group that looks something like this
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
The number of noteblocks depends on the note's dynamic level,
this diagram shows one with maximum dynamic level 4.

Upon being called, the generator fills the required space
starting from the build c with air, then generates the structure.

## License

Do whatever you want.