# Noteblock generator
Generate music in Minecraft noteblocks.

This program is only intended for my own use, and shared only for others to replicate my builds.

See my projects:
* [Handel's He trusted in God](https://github.com/FelixFourcolor/He-trusted-in-God)
* [Bach's Sind Blitze, sind Donner](https://github.com/FelixFourcolor/Sind-Blitze-sind-Donner)
* [Bach's Herr, unser Herrscher](https://github.com/FelixFourcolor/Herr-unser-Herrscher)
* [Mozart's Confutatis](https://github.com/FelixFourcolor/Confutatis)
* [Mozart's Dies irae](https://github.com/FelixFourcolor/Dies-irae)
* [Mozart's Sull'aria](https://github.com/FelixFourcolor/Canzonetta-sull-aria)

## Requirements
* Minecraft java 1.19+
* python 3.10+

## Installation:
```pip install --upgrade noteblock-generator```

Do not use git version, it is for development (i.e. myself) only. I cannot guarantee that it is compatible with all of my projects.

## Usage
```
noteblock-generator [-h] [--location [LOCATION ...]] [--orientation [ORIENTATION ...]] [--theme THEME] [--blend] path_in path_out

positional arguments:
  path_in                         path to music source file/folder
  path_out                        path to Minecraft world

options:
  -h, --help                      show this help message and exit
  --location [LOCATION ...]       build location (in x y z); default is ~ ~ ~
  --dimension DIMENSION           build dimension; default is player's dimension
  --orientation [ORIENTATION ...] build orientation (in x y z); default is + + +
  --theme THEME                   opaque block for redstone components; default is stone
  --blend                         blend the structure in with its environment (EXPERIMENTAL)
```

### Path in
Path to a music file, or a folder containing multiple music files.

This program is only intended for my own use, so there is no documentation for writing music files. Follow my `Build from source` instructions to replicate my builds.

### Path out
Path to a Minecraft world save folder.

### Location
The location where the structure will be generated.

This uses Minecraft's relative coordinates syntax, where `~` stands for the player's location. For example, `--location ~ ~ ~` (default) is the player's current location, `--location ~ ~10 ~` is 10 blocks above the player, etc.

Warning: If you are on a Unix operating system, the character `~` must be escaped (e.g. the above example would be `--location \~ ~10 \~`).


### Dimension
The dimension where the structure will be generated. 

Valid choices are `overworld`, `the_nether`, `the_end`.

If not given, it will be the player's current dimension.

### Orientation
In which direction, from the aforementioned location, the structure will be generated.

`--orientation + + +` (default) means the structure will be generated towards the positive x, positive y, positive z directions.

All valid orientations are `+ + +`, `+ + -`, `+ - +`, `+ - -`, `- + +`, `- + -`, `+ + +`, `+ + -`, `+ - +`, `+ - -`.

Note: Make sure there is enough space in your specified direction. The program cannot generate below bedrock, or above the height limit, etc. For example,`--location 0 -64 0 --orientation + - +` will not work.

### Theme
Choose a block that can conduct redstones for the basis of the structure. Default is `stone`.

Consult Minecraft's documentation for what blocks can conduct redstone and their technical names (java version).

### Blend
By default, the program will clear the entire space before generating. With `--blend`, it will place noteblocks and redstone components where they need to be, remove things that may interfere with the redstones (e.g. water), and leave the rest as-is. The result is the structure will appear blended in with its environment, which in my opinion looks quite nice.

This is an experimental feature (the list of things to be removed is continually updated). If the redstones and/or noteblocks don't behave as expected, turn it off.
