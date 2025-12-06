import type { LazySong, LoadedSong } from "@/core/loader";
import { ResolverCache } from "./cache";
import { resolveSong, type SongResolution } from "./components";

export function resolve(song: LoadedSong): Promise<SongResolution> {
	return resolveSong(song);
}

export function cachedResolver() {
	const cache = new ResolverCache();
	const cacheInvalidate = cache.invalidate.bind(cache);

	return ({ song, updates }: Awaited<ReturnType<LazySong>>) => {
		updates.forEach(cacheInvalidate);
		return resolveSong(song, cache);
	};
}
