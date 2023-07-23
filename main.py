#!/usr/bin/env python
import json
import sys

from music import Composition

with open(sys.argv[1], "r") as f:
    kwargs = json.load(f)

composition = Composition(**kwargs)

print(composition)
for voice in composition:
    print(voice)
    for bar in voice:
        print(bar)
