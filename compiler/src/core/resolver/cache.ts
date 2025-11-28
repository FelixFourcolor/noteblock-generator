import type { FileRef, IProperties } from "#schema/@";
import type { Tick } from "./components/tick.js";
import type { VoiceResolution } from "./components/voice.js";

type CacheKey = {
	songModifier: IProperties;
	level: number;
	voiceModifier?: IProperties;
	url: FileRef;
};

export class ResolverCache {
	dependencies = new Set<string>();

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
		this.dependencies.add(key.url.slice(7));

		return { ...value, ticks: toGenerator(ticks) };
	}

	async invalidate(filePath: string) {
		const voice = toFileRef(filePath);
		const key = this.cacheKeys.get(voice);
		if (key) {
			this.cacheKeys.delete(voice);
			this.cache.delete(key);
		}
	}

	exportDataForTests() {
		return Object.fromEntries(
			this.dependencies
				.values()
				.map((filePath) => [
					filePath,
					this.cache.get(this.cacheKeys.get(toFileRef(filePath))!)!,
				]),
		);
	}
}

function toFileRef(filePath: string): FileRef {
	if (!filePath.match(/^\.*\//)) {
		filePath = `./${filePath}`;
	}
	return `file://${filePath}` as FileRef;
}

function toGenerator<T>(array: T[]): Generator<T> {
	function* generator() {
		yield* array;
	}
	return generator();
}
