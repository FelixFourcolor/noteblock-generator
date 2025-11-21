import { match } from "ts-pattern";
import type { SongLayout } from "#core/assembler/@";
import type { Building } from "./builders/builder.js";
import { DoubleBuilder } from "./builders/double-builder.js";
import { SingleBuilder } from "./builders/single-builder.js";
import type { BuilderCache } from "./cache.js";

export function build(song: SongLayout, cache?: BuilderCache): Building {
	return match(song)
		.with({ type: "single" }, (song) => new SingleBuilder(song, cache))
		.with({ type: "double" }, (song) => new DoubleBuilder(song, cache))
		.exhaustive()
		.build();
}
