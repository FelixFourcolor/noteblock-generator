import { match } from "ts-pattern";
import type { SongLayout } from "@/core/layout";
import type { Building, BuildOptions } from "./builder";
import { DoubleBuilder } from "./double-builder";
import { SingleBuilder } from "./single-builder";
import { BuilderCache } from "./utils/cache";

export function build(song: SongLayout, options: BuildOptions): Building {
	return _build(song, options);
}

type LiveBuildOptions = BuildOptions & { emit: "full" | "diff" };

export function cachedBuilder(options: LiveBuildOptions) {
	const cache = new BuilderCache();

	return (song: SongLayout) => {
		const data = _build(song, options, cache);
		if (options.emit === "diff") {
			return data;
		}
		return cache.merge(data);
	};
}

const _build = (
	song: SongLayout,
	options: BuildOptions,
	cache?: BuilderCache,
) =>
	match(song)
		.with({ type: "single" }, (song) => new SingleBuilder(song, options, cache))
		.with({ type: "double" }, (song) => new DoubleBuilder(song, options, cache))
		.exhaustive()
		.build();
