import type { FileRef, IProperties } from "@/types/schema";
import type { Tick, VoiceResolution } from "./components";

type CacheKey = {
	songModifier: IProperties;
	level: number;
	voiceModifier: IProperties;
	url: FileRef;
};

export class ResolverCache {
	private cacheKeys = new Map<FileRef, string>();
	private cache = new Map<
		string,
		Omit<VoiceResolution, "ticks"> & { ticks: Tick[] }
	>();

	get(key: CacheKey): VoiceResolution | undefined {
		const cached = this.cache.get(JSON.stringify(key));
		if (!cached) {
			return undefined;
		}
		return { ...cached, ticks: toGenerator(cached.ticks) };
	}

	set(key: CacheKey, value: VoiceResolution): VoiceResolution {
		const ticks = Array.from(value.ticks);

		const serializedKey = JSON.stringify(key);
		this.cache.set(serializedKey, { ...value, ticks });
		this.cacheKeys.set(key.url, serializedKey);

		return { ...value, ticks: toGenerator(ticks) };
	}

	invalidate(url: FileRef) {
		const key = this.cacheKeys.get(url);
		if (key === undefined) {
			throw new Error("Attempted to invalidate non-existent cache entry.");
		}
		this.cacheKeys.delete(url);
		this.cache.delete(key);
	}

	exportData() {
		return this.cacheKeys
			.entries()
			.map(([url, key]) => [url, this.cache.get(key)!] as const);
	}
}

function toGenerator<T>(array: T[]): Generator<T> {
	function* generator() {
		yield* array;
	}
	return generator();
}
