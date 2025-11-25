import { isEmpty } from "lodash";
import { match } from "ts-pattern";
import type { SongLayout } from "#core/assembler/@";
import type { Building } from "./builders/builder.js";
import { DoubleBuilder } from "./builders/double-builder.js";
import { SingleBuilder } from "./builders/single-builder.js";
import { BuilderCache } from "./cache.js";

export function build(song: SongLayout): Building {
	return _build(song);
}

type Builder = (song: SongLayout) => Building | undefined;

export function cachedBuilder(options: { emit: "full" | "diff" }): Builder {
	const cache = new BuilderCache();

	return (song: SongLayout): Building | undefined => {
		const building = _build(song, cache);
		if (options.emit === "full") {
			return cache.update(building);
		}
		if (!isEmpty(building.blocks)) {
			return building;
		}
	};
}

function _build(song: SongLayout, cache?: BuilderCache) {
	return match(song)
		.with({ type: "single" }, (song) => new SingleBuilder(song, cache))
		.with({ type: "double" }, (song) => new DoubleBuilder(song, cache))
		.exhaustive()
		.build();
}
