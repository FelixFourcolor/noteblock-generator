# Noteblock generator
Generate music in Minecraft noteblocks.

My projects using this program:
* [Handel's He trusted in God](https://github.com/FelixFourcolor/He-trusted-in-God)
* [Bach's Sind Blitze, sind Donner](https://github.com/FelixFourcolor/Sind-Blitze-sind-Donner)
* [Bach's Herr, unser Herrscher](https://github.com/FelixFourcolor/Herr-unser-Herrscher)
* [Mozart's Confutatis](https://github.com/FelixFourcolor/Confutatis)
* [Mozart's Dies irae](https://github.com/FelixFourcolor/Dies-irae)

## Requirements
* Minecraft java 1.18+
* python 3.10+

## Installation:
```pip install --upgrade noteblock-generator```

## Usage
```
noteblock-generator [-h] [--location [LOCATION ...]] [--orientation [ORIENTATION ...]] [--theme THEME] [--clear] path_in path_out

positional arguments:
  path_in               path to music source file(s)
  path_out              path to Minecraft world

options:
  -h, --help            show this help message and exit
  --location [LOCATION ...]
                        build location (in x y z); default is ~ ~ ~
  --dimension DIMENSION
                        build dimension; default is player's dimension
  --orientation [ORIENTATION ...]
                        build orientation (in x y z); default is + + +
  --theme THEME
                        opaque block for redstone components; default is stone
  --clear               clear the space before generating
```

### Path in
Path to a music file, or a folder containing multiple music files.

At this point in time this program is only intended for my own use, so there is no documentation for writing music files. Follow the `build from source` instructions in my projects in order to replicate my builds.

### Path out
Path to a Minecraft world save folder.

### Location
The location where the structure will be generated.

This uses Minecraft's relative coordinates syntax, where `~` stands for the player's location. For example, `--location ~ ~ ~` (default) is the player's current location, `--location ~ ~10 ~` is 10 blocks above the player, etc.

Notes: In Unix operating systems, `~` is a special character that stands for the home directory, make sure to escape it.


### Dimension
The dimension where the structure will be generated. 

Valid choices are `overworld`, `the_nether`, `the_end`.

If not given, it will be the player's current dimension.

### Orientation
In which direction, from the aforementioned location, the structure will be generated.

`--orientation + + +` (default) means the structure will be generated towards the positive x, positive y, positive z directions.

All valid orientations are `+ + +`, `+ + -`, `+ - +`, `+ - -`, `- + +`, `- + -`, `+ + +`, `+ + -`, `+ - +`, `+ - -`.

Note: Make sure there is enough space in your specified direction in order to generate. The program cannot generate below bedrock, or above the height limit, etc. For example, if you are at y=-64, `--location ~ ~ ~ --orientation + - +` will not work.

### Theme
Choose a block that can conduct redstones to theme the structure. Default is `stone`.

Consult Minecraft's documentation for what blocks can conduct redstone and their technical names (java version).

### Clear
`--clear` will clear the space before generating. This guarantees nothing may be in the way that interferes with the redstones or note blocks. But this option makes the program much slower.

Rule of thumb: Use `--clear` just to be safe, unless you know what you're doing.

## License

This program is given to the public domain. No rights reserved.
