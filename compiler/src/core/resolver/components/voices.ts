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

	const resolveVoiceWithCache: typeof resolveVoice = cache
		? async (voice, ctx) => {
				if (!is<FileRef>(voice)) {
					return resolveVoice(voice, ctx);
				}
				const cacheKey = { ...ctx, voice };
				return (
					cache.get(cacheKey) ??
					resolveVoice(voice, ctx).then((res) => cache.set(cacheKey, res))
				);
			}
		: resolveVoice;

	const voices = entries
		.reverse()
		.map((entry, index) => {
			if (entry === null) {
				return null;
			}
			if (!Array.isArray(entry)) {
				return resolveVoiceWithCache(entry, { ...ctx, index });
			}
			return merge(
				entry.map((subvoice, subIndex) => {
					return resolveVoiceWithCache(subvoice, {
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
