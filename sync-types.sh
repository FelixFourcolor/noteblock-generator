#!/bin/bash

ROOT=$(realpath "$(dirname "$0")")

TS_FILE="$ROOT/compiler/src/api/types.d.ts"
PY_FILE="$ROOT/generator/noteblock_generator/api/types.py"

{
    echo -e '"""Transpiled from TypeScript."""\n'
    npx --silent typescript2python $TS_FILE --strict
} > $PY_FILE
