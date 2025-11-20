import type { Tick, VoiceContext, VoiceResolution } from "#core/resolver/@";
import type { FileRef } from "#schema/@";

type CacheKey = VoiceContext & { voice: FileRef };

export class ResolutionCache {
	dependencies = new Set<string>();

	private data = new Map<
		string,
		Omit<VoiceResolution, "ticks"> & { ticks: Tick[] }
	>();
	private cacheKeyMap = new Map<string, string>();

	get(key: CacheKey): VoiceResolution | undefined {
		const cached = this.data.get(JSON.stringify(key));
		if (!cached) {
			return undefined;
		}
		return {
			...cached,
			// biome-ignore format: prettier in one line
			ticks: (function* () { yield* cached.ticks; })(),
		};
	}

	set(key: CacheKey, value: VoiceResolution): VoiceResolution {
		const ticks = Array.from(value.ticks);

		const serializedKey = JSON.stringify(key);
		this.data.set(serializedKey, { ...value, ticks });
		this.cacheKeyMap.set(key.voice, serializedKey);
		this.dependencies.add(key.voice.slice(7));

		return {
			...value,
			// biome-ignore format: prettier in one line
			ticks: (function* () { yield* ticks; })(),
		};
	}

	async invalidate(filePath: string) {
		if (!filePath.match(/^\.*\//)) {
			filePath = `./${filePath}`;
		}
		const voice = `file://${filePath}`;
		const key = this.cacheKeyMap.get(voice);
		if (key) {
			this.cacheKeyMap.delete(voice);
			this.data.delete(key);
		}
	}
}
