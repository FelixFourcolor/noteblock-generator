#!/bin/bash

root=$(realpath "$(dirname "$0")")
TS_file="$root/../compiler/src/api/types.d.ts"
PY_file="$root/../generator/noteblock_generator/api/types.py"
{
    echo -e '"""Transpiled from TypeScript."""\n'
    npx --silent typescript2python $TS_file --strict
} > $PY_file
