import { UserError } from "#cli/error.js";
import type { LazyVoiceEntry } from "#core/loader/@";
import type { ResolverCache } from "#core/resolver/cache.js";
import type { IProperties } from "#schema/@";
import { zip } from "../utils/generators.js";
import { resolveVoice, type VoiceResolution } from "../voice/voice.js";

export type SongContext = { songModifier: IProperties; cwd: string };

export async function resolveVoices(
	entries: LazyVoiceEntry[],
	songModifier: IProperties,
	cache?: ResolverCache,
): Promise<VoiceResolution> {
	async function merge(voices: Promise<VoiceResolution>[]) {
		const voiceResolutions = await Promise.all(voices);
		return {
			type: voiceResolutions.map(({ type }) => type).includes("double")
				? ("double" as const)
				: ("single" as const),
			time: voiceResolutions[0]!.time,
			ticks: zip(voiceResolutions.map(({ ticks }) => ticks)),
		};
	}

	const cachedResolveVoice = resolveVoiceWithCache(cache);

	const voices = entries
		.toReversed()
		.map((entry, index) => {
			if (entry === null) {
				return null;
			}
			if (!Array.isArray(entry)) {
				return cachedResolveVoice(entry, songModifier, index);
			}
			return merge(
				entry.map((subvoice, subIndex) => {
					return cachedResolveVoice(subvoice, songModifier, [index, subIndex]);
				}),
			);
		})
		.filter((e) => e !== null);

	if (voices.length === 0) {
		throw new UserError("Song is empty.");
	}

	return merge(voices);
}

function resolveVoiceWithCache(cache?: ResolverCache): typeof resolveVoice {
	if (!cache) {
		return resolveVoice;
	}

	return (voice, songModifier, index) => {
		const cacheKey = (() => {
			const { url, modifier: voiceModifier = {} } = voice;
			if (!url) {
				return null;
			}
			const level = typeof index === "number" ? index : index[0];
			return { songModifier, voiceModifier, url, level };
		})();

		if (!cacheKey) {
			return resolveVoice(voice, songModifier, index);
		}

		const cachedResult = cache.get(cacheKey);
		if (cachedResult) {
			return Promise.resolve(cachedResult);
		}

		return resolveVoice(voice, songModifier, index).then((res) =>
			cache.set(cacheKey, res),
		);
	};
}
