#!/bin/bash

ROOT=$(realpath "$(dirname "$0")")

transpile() {
    # must cd because typescript2python only lives inside compiler
    cd "$ROOT/compiler"
    local ts_file="src/api/types.d.ts"
    npx --silent typescript2python "$ts_file" --strict
}

generate() {
    cd "$ROOT/generator"
    local py_file="noteblock_generator/api/types.py"
    {
        echo -e '"""Transpiled from TypeScript."""\n'
        transpile
    } > "$py_file"
}

generate