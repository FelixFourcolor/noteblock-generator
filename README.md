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

## Usage
```
noteblock-generator path/to/music/source path/to/minecraft/world [--OPTIONS]

Options:
  --location [LOCATION ...]       build location (in '<x> <y> <z>'); default is player's location
  --dimension DIMENSION           build dimension; default is player's dimension
  --orientation [ORIENTATION ...] build orientation (in '<horizontal> <vertical>'); default is player's orientation
  --theme THEME                   redstone-conductive block; default is stone
  --blend                         blend the structure with its environment
  --quiet                         suppress all text outputs, unless an error occurs
```

### Music source
Path to the music source. This program is only intended for my own use, so there is no documentation for writing music files. Follow my `Build from source` instructions to replicate my builds.

### Minecraft world
Path to an existing minecraft world. Only Java Edition is supported.

On Linux the save folder is probably at `~/.minecraft/saves`. On Windows it's probably at `C:\Users\<username>\AppData\Roaming\.minecraft\saves`.

### Location
The location where the structure will be generated.

This uses Minecraft's relative coordinates syntax, where `~` stands for the player's location. For example, `--location ~ ~ ~` (default) is the player's current location, `--location ~ ~10 ~` is 10 blocks above the player, etc.

Warning: On Linux (and similar platforms), the character `~` must be escaped (e.g. the above example would be `--location \~ ~10 \~`).

### Dimension
The dimension where the structure will be generated. Valid choices are `overworld`, `the_nether`, `the_end`.

If not given, it will be the player's current dimension.

### Orientation
The orientation towards which the structure will be generated.

This uses Minecaft's rotation syntax, which is a pair of two numbers, the first one for horizontal, the second one for vertical. Horizontal rotation goes from -180 to 180, where -180 is north, -90 is east, 0 is south, 90 is east, and 180 is wrapping back to north. Vertical rotation goes form -90 to 90, where -90 is looking straight up and 90 is straight down.

Similarly to location, either value of the pair (or both) can be substituted with a `~` to use the player's orientation. For example, `--orientation ~ 90` means facing the same horizontal direction as the player, looking down.

### Theme
Choose a block that can conduct redstones. Default is `stone`

Consult Minecraft's documentation for what blocks can conduct redstone and their technical names (java version).

### Blend
By default, the program will clear the entire space before generating. With `--blend`, it will place noteblocks and redstone components where they need to be, remove things that may interfere with the redstones (e.g. water), and leave the rest. The result is the structure will appear blended in with its environment.

## Quiet
Suppress all text outputs, unless an error occurs. Outputs include diagnostic information about the music and the minecraft world, as well as user confirmation dialogs in important steps (suppressed = agree to all).