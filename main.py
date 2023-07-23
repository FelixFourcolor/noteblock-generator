#!/usr/bin/env python
import json
import sys

from music import Composition


class UserError(Exception):
    pass


def excepthook(exc_type, exc_value, exc_tb):
    if exc_type is UserError:
        print(exc_value)
    else:
        print(f"{exc_type.__name__}: {exc_value}")


sys.excepthook = excepthook

try:
    path_in = sys.argv[1]
    path_out = sys.argv[2]
    # so that error is raised when 3+ arguments are provided
    try:
        sys.argv[3]
    except IndexError:
        pass
    else:
        raise IndexError
except IndexError:
    raise UserError(
        "Invalid arguments; expected paths to input file and output Minecraft world."
    )

with open(path_in, "r") as f:
    try:
        json_composition = json.load(f)
    except Exception:
        raise UserError(f"Failed to parse {path_in}.")

try:
    json_voices: list[dict] = json_composition.pop("voices")
except KeyError as e:
    raise UserError(f"{path_in} is missing required {e} field.")

composition = Composition(**json_composition)

for json_voice in json_voices:
    try:
        json_notes: list[dict | str] = json_voice.pop("notes")
    except KeyError as e:
        raise UserError(f"{path_in}.voices is missing required {e} field.")

    voice = composition.add_voice(**json_voice)

    for json_note in json_notes:
        if isinstance(json_note, str):
            json_note = {"name": json_note}
        voice.add_note(**json_note)

print(composition)
for voice in composition:
    print(voice)
    for bar in voice:
        print(bar)

composition.generate(path_out)
