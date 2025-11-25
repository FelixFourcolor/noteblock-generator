# Noteblock generator

This is a project that takes human-readable music notation in plain text and generates a note block structure in Minecraft. The notation is a language I made up, loosely inpired by [lilypond](https://lilypond.org/), with features specifically designed for note block music.

There are two separate programs, a [compiler](#compiler) and a [generator](#generator).

## Compiler

The compiler takes the music source and outputs an intermediate representation of the note block structure.

### Setup

<table>
  <tr>
    <th>Requires</th>
    <td>Node.js >= 22</td>
  </tr>
  <tr>
    <th>Install</th>
    <td><code>npm install noteblock-compiler</code></td>
  </tr>
</table>
<br/>

After installing, the `nbc` command should be available. Run `nbc --help` to verify.

### Usage

Music is written in YAML format. The simplest use case is just an array of note names:

```sh
# twinkle twinkle little star
echo "[c, c, g, g, a, a, g]" | nbc
```

<details>
<summary> What the output looks like</summary>

```jsonc
{
  "size": { "height": 6, "length": 11, "width": 36 },
  "blocks": {
    "7 2 18": 0,
    "7 1 17": 0,
    "7 2 17": "repeater[facing=south]",
    "7 0 16": 0,
    "7 1 16": "redstone_wire[east=side,west=side]",
    "7 2 16": 0,
    "7 1 15": 0,
    "6 0 16": "air",
    "6 1 16": "note_block[note=13]",
    "6 2 16": "air",
    "8 1 16": null,
    "6 1 15": null,
    "8 1 15": null,
    "5 1 16": null,
    "9 1 16": null,
    "7 2 15": "repeater[facing=south]",
    "7 0 14": 0,
    "7 1 14": "redstone_wire[east=side,west=side]",
    "7 2 14": 0,
    "7 1 13": 0,
    "6 0 14": "air",
    "6 1 14": "note_block[note=13]",
    "6 2 14": "air",
    "8 1 14": null,
    "6 1 13": null,
    "8 1 13": null,
    "5 1 14": null,
    "9 1 14": null,
    "7 2 13": "repeater[facing=south]",
    "7 0 12": 0,
    "7 1 12": "redstone_wire[east=side,west=side]",
    "7 2 12": 0,
    "7 1 11": 0,
    "6 0 12": "air",
    "6 1 12": "note_block[note=13]",
    "6 2 12": "air",
    // ...
    // truncated, actual output is very large
  }
}
```

</details>

A typical project would have a main file that defines the song, and a separate file for each voice. For example:

```txt
src/
├─ index.yaml
├─ piano/
│  ├─ left-hand.yaml
│  ├─ right-hand.yaml
├─ strings/****
│  ├─ violin.yaml
│  ├─ cello.yaml
```

To compile a single-file project, you can just pipe the file into `nbc` like above. For multi-file projects, provide the main file as an option parameter:

```sh
nbc -i src/index.yaml
```

### Features

If placing blocks yourself in-game is like writing machine code by hand, and using an auto-generator from a MIDI file is like asking an LLM to write the code for you, then this compiler is like assembly or C. There are some abstractions to ease the process, but you retain very fine control over the output.

Features include:

- Mixing instruments (one note played by multiple blocks of different instruments)
- Customizable sustain length. For example, a note's duration may be 4 redstone ticks, but you can make it only sustained for 3 ticks, leaving the last tick silent.
- Two ways to control volume:
  - Multiplicity-based: how many blocks used to play the note.
  - Position-based: How far away the note block is from the player.
- Volume can vary during a note's duration (e.g., to create onset and/or fade-out).
- When mixing instruments, each can have its own sustain & volume settings.
- Any setting can be changed mid-song.

Since this tool is only intended for my own use, **there is no documentation** for how to use this language.

## Generator

The generator takes the compiler's output and generates the structure in-game.

### Setup

<table>
  <tr>
    <th>Requires</th>
    <td>Python >= 3.10</td>
  </tr>
  <tr>
    <th>Install</th>
    <td><code>pip install noteblock-generator</code></td>
  </tr>
</table>
<br/>

After installing, the `nbg` command should be available. Run `nbg --help` to verify.

### Basic usage

```sh
nbg -i path/to/compiler/output -o path/to/minecraft/world
```

You can also pipe the compiler's output directly into the generator.

```sh
nbc [options] | nbg -o path/to/minecraft/world
```

### Theming

To find themes, go to the Minecraft wiki for the block you like (must be [redstone-conductive](https://minecraft.wiki/w/Conductivity)), scroll down to "Data values", and use the block's identifier for Java edition ([example page](https://minecraft.wiki/w/Block_of_Copper#Data_values)).

| `--theme packed_ice` | `--theme gold_block` |
| :-: | :-: |
| ![ice theme](images/ice-theme.png) | ![gold theme](images/gold-theme.png) |

If the block has states, you can specify them inside square brackets.

| `--theme cherry_log[axis=x]` | `--theme cherry_log[axis=y]` |
| :-: | :-: |
| ![cherry_log axis=x](images/axis-x.png) | ![cherry_log axis=y](images/axis-y.png) |

You can use `--theme` (or `-t` for short) multiple times. Theme blocks will be distributed evenly across the structure's width from left to right.

`-t blue_ice -t stripped_cherry_log -t white_wool -t stripped_cherry_log -t blue_ice`
![multi theme](images/multi-theme.png)

### Blending

By default, the program clears the entire space that the structure will occupy before generating. With the `--blend` flag, the structure will generate into the terrain, leaving existing blocks intact.

| Default | `--blend` |
| :-: | :-: |
| ![without --blend](images/no-blend.png) | ![with --blend](images/blend.png) |

### Positioning

By default, the structure is generated wherever your character is. But you can fully customize the position. For example,

```sh
nbg -i compiled.json -o path/to/world
    --dim   nether      # in the nether
    --at    10 80 500   # starting from x=10, y=80, z=500
    --face  +X          # generate towards the positive X direction
    --align left        # to the player's left
    --tilt  down        # underneath the player's feet
```

will result in

```text
^                                   ^
| X                                 | Y
|                                   |
|      ----------------             - 80   ---------------@
|      |              |             |      |              |
|      |     the      |             |      |     the      |
|      |  structure   |             |      |  structure   |
|      |              |             |      |              |
|      | (above view) |             |      | (side view)  |
|      |              |             |      |              |
- 10   ---------------@             |      ----------------
|                                   |
|                    500   Z        |                    500   Z
----------------------|----->       ----------------------|----->
```
