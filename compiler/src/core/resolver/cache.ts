import type { Tick, VoiceContext, VoiceResolution } from "#core/resolver/@";
import type { FileRef } from "#schema/@";

type CacheKey = VoiceContext & { voice: FileRef };
type SerializedResolution = Omit<VoiceResolution, "ticks"> & { ticks: Tick[] };

export class ResolutionCache {
	dependencies = new Set<string>();

	private cacheKeys = new Map<FileRef, string>();
	private cache = new Map<string, SerializedResolution>();

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
		this.cacheKeys.set(key.voice, serializedKey);
		this.dependencies.add(key.voice.slice(7));

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

	/** For integration tests only */
	exportData() {
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
	return `file://${filePath}`;
}

function toGenerator<T>(array: T[]): Generator<T> {
	function* generator() {
		yield* array;
	}
	return generator();
}
