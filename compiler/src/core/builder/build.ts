import { match } from "ts-pattern";
import type { SongLayout } from "#core/assembler/@";
import { DoubleBuilder, SingleBuilder } from "#core/builder/builders/@";
import type { BuildingDTO } from "./types.js";

export function build(song: SongLayout): BuildingDTO {
	const builder = match(song)
		.with({ type: "single" }, (song) => new SingleBuilder(song))
		.with({ type: "double" }, (song) => new DoubleBuilder(song))
		.exhaustive();
	return builder.build();
}
