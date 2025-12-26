import { match } from "ts-pattern";
import type { SongLayout } from "@/core/layout";
import type { Building } from "./builder";
import { DoubleBuilder } from "./double-builder";
import { SingleBuilder } from "./single-builder";
import { BuilderCache } from "./utils/cache";

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
