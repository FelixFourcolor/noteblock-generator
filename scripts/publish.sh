#!/bin/bash

ROOT=$(cd "$(dirname "$0")/.." && pwd)

sed -E 's|\(images/([^\\s]+)\)|\(https://github.com/FelixFourcolor/noteblock-generator/blob/main/images/\1?raw=true\)|g' "$ROOT/README.md" > "$ROOT/README.pub.md"

(
    cd "$ROOT/compiler"
    cp "$ROOT/README.pub.md" ./README.md
    pnpm build
    pnpm publish --no-git-checks
    rm README.md
) &
compiler_build=$!

(
    cd "$ROOT/generator"
    cp "$ROOT/README.pub.md" ./README.md
    uv build
    uv publish
    rm README.md
    rm -r dist
) &
generator_build=$!

wait $compiler_build
wait $generator_build

rm "$ROOT/README.pub.md"