import { is } from "typia";
import { UserError } from "#cli/error.js";
import type { ResolverCache } from "#core/resolver/cache.js";
import type { FileRef, IProperties, VoiceEntry } from "#schema/@";
import { zip } from "./utils/generators.js";
import { resolveVoice, type VoiceResolution } from "./voice.js";

export type SongContext = { songModifier: IProperties; cwd: string };

export async function resolveVoices(
	entries: VoiceEntry[],
	ctx: SongContext,
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
		.reverse()
		.map((entry, index) => {
			if (entry === null) {
				return null;
			}
			if (!Array.isArray(entry)) {
				return cachedResolveVoice(entry, { ...ctx, index });
			}
			return merge(
				entry.map((subvoice, subIndex) => {
					return cachedResolveVoice(subvoice, {
						...ctx,
						index: [index, subIndex],
					});
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

	return (voice, ctx) => {
		const cacheKey = (() => {
			const { songModifier, index } = ctx;
			const level = typeof index === "number" ? index : index[0];
			if (is<FileRef>(voice)) {
				return { songModifier, level, url: voice };
			}
			const { notes, ...voiceModifier } = voice;
			if (is<FileRef>(notes)) {
				return { songModifier, voiceModifier, level, url: notes };
			}
			return null;
		})();

		if (!cacheKey) {
			return resolveVoice(voice, ctx);
		}

		const cachedResult = cache.get(cacheKey);
		if (cachedResult) {
			return Promise.resolve(cachedResult);
		}

		return resolveVoice(voice, ctx).then((res) => cache.set(cacheKey, res));
	};
}
