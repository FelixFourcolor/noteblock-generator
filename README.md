# Noteblock generator
This program is only intended for my own use, and shared only for others to replicate my builds.

See my projects:
* [Handel's He trusted in God](https://github.com/FelixFourcolor/He-trusted-in-God)
* [Bach's Sind Blitze, sind Donner](https://github.com/FelixFourcolor/Sind-Blitze-sind-Donner)
* [Bach's Herr, unser Herrscher](https://github.com/FelixFourcolor/Herr-unser-Herrscher)
* [Mozart's Confutatis](https://github.com/FelixFourcolor/Confutatis)
* [Mozart's Dies irae](https://github.com/FelixFourcolor/Dies-irae)
* [Mozart's Sull'aria](https://github.com/FelixFourcolor/Canzonetta-sull-aria)
* [Handel's And the glory of the Lord](https://github.com/FelixFourcolor/And-the-glory-of-the-Lord)

## Requirements
* Minecraft Java 1.19+
* Python 3.10-3.12

## Installation
```pip install --upgrade noteblock-generator```

## Usage
```
usage: noteblock-generator path/to/music/source path/to/minecraft/world [--OPTIONS]

build options:
  -l/--location X Y Z                  build location; default is player's location
  -d/--dimension DIMENSION             build dimension; default is player's dimension
  -o/--orientation HORIZONTAL VERTICAL build orientation; default is player's orientation
  -t/--theme BLOCK                     redstone-conductive block; default is stone
  --blend                              blend the structure with its environment

output options:
  -q/--quiet                           decrease output verbosity; can be used up to 3 times
  --debug                              show full exception traceback if an error occurs

help:
  -h/--help                            show this help message and exit
```

### Music source
Path to the music source. It should be provided to you in all of my projects.

### Minecraft world
Path to an existing minecraft world. Only Java Edition is supported.

Consult Minecraft's documentation (or your custom launcher's documentation if you use one) for where the save folder is.

### Location
The location where the structure will be generated.

This uses Minecraft's relative coordinates syntax, where `~` stands for the player's location. For example, `--location ~ ~ ~` (default) is the player's current location, `--location ~ ~10 ~` is 10 blocks above the player, etc.

### Dimension
The dimension where the structure will be generated. If not given, it will be the player's current dimension.

### Orientation
The orientation towards which the structure will be generated.

This uses Minecaft's rotation syntax, which is a pair of two numbers, the first one for horizontal, the second one for vertical. Horizontal rotation goes from -180 to 180, where -180 is north, -90 is east, 0 is south, 90 is east, and 180 is wrapping back to north. Vertical rotation goes form -90 to 90, where -90 is looking straight up and 90 is straight down.

Similarly to location, either value of the pair (or both) can be substituted with a `~` to use the player's current orientation. For example, `--orientation ~ 90` means facing the same horizontal direction as the player, looking down.

### Theme
Choose a block that can conduct redstones. Default is `stone`

Consult Minecraft's documentation for what blocks can conduct redstone and their technical names (Java Edition).

### Blend
By default, the program will clear the entire space before generating. With `--blend`, it will place noteblocks and redstone components where they need to be, remove things that may interfere with the redstones (e.g. water), and leave the rest. The result is the structure will appear blended in with its environment.

### Verbosity
There are 4 verbosity levels, from least to most verbose is:

* `-qqq`: No output at all, even if an error occurs, only an exit status to indicate success.
* `-qq`: Above, plus critical warnings, and a brief error message if one occurs.
* `-q`: Above, plus brief information about the structure, a generating progress bar, and longer error message if one occurs.
* Default: Above, plus full information about the structure, and a confirmation prompt before generating.

Note: with `-q` option, without a confirmation prompt, you can still press `CTRL + C` before the progress bar reaches 100% to safely quit the program; no changes would be made to the world.
