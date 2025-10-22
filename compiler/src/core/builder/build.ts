import { match } from "ts-pattern";
import type { SongLayout } from "#core/assembler/@";
import type { Building } from "./builders/builder.js";
import { DoubleBuilder } from "./builders/double-builder.js";
import { SingleBuilder } from "./builders/single-builder.js";

export function build(song: SongLayout): Building {
	const builder = match(song)
		.with({ type: "single" }, (song) => new SingleBuilder(song))
		.with({ type: "double" }, (song) => new DoubleBuilder(song))
		.exhaustive();
	return builder.build();
}
