import { match } from "ts-pattern";
import type { SongLayout } from "#core/layout/@";
import type { Building } from "./builders/builder.js";
import { DoubleBuilder } from "./builders/double-builder.js";
import { SingleBuilder } from "./builders/single-builder.js";
import { BuilderCache } from "./cache.js";

export function build(song: SongLayout): Building {
	return _build(song);
}

export function cachedBuilder(options: {
	emit: "full" | "diff";
}): typeof build {
	const cache = new BuilderCache();

	return (song) => {
		const data = _build(song, cache);
		if (options.emit === "diff") {
			return data;
		}
		return cache.merge(data);
	};
}

const _build = (song: SongLayout, cache?: BuilderCache) =>
	match(song)
		.with({ type: "single" }, (song) => new SingleBuilder(song, cache))
		.with({ type: "double" }, (song) => new DoubleBuilder(song, cache))
		.exhaustive()
		.build();
