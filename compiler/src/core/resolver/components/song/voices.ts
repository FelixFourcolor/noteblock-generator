import { UserError } from "#cli/error.js";
import type { VoiceEntry } from "#schema/@";
import { zipAsync } from "../generator-utils.js";
import type { SongContext, VoiceResolution } from "../resolution.js";

export async function resolveVoices(
	entries: VoiceEntry[],
	ctx: SongContext,
): Promise<VoiceResolution> {
	const THRESHOLD_TO_USE_WORKER = 6;
	const useWorker = entries.flat().length >= THRESHOLD_TO_USE_WORKER;
	const { resolveVoice } = useWorker
		? await import("../voice/voice-threaded.js")
		: await import("../voice/voice.js");

	async function merge(voices: Promise<VoiceResolution>[]) {
		const VoiceResolutions = await Promise.all(voices);
		return {
			type: VoiceResolutions.map(({ type }) => type).includes("double")
				? ("double" as const)
				: ("single" as const),
			time: VoiceResolutions[0]!.time,
			ticks: zipAsync(VoiceResolutions.map(({ ticks }) => ticks)),
		};
	}

	const voices = entries
		.reverse()
		.map((entry, index) => {
			if (entry === null) {
				return null;
			}
			const voiceCtx = { ...ctx, index };
			if (!Array.isArray(entry)) {
				return resolveVoice(entry, voiceCtx);
			}
			return merge(entry.map((subvoice) => resolveVoice(subvoice, voiceCtx)));
		})
		.filter((e) => e !== null);

	if (voices.length === 0) {
		throw new UserError("Song must contain at least one voice.");
	}

	return merge(voices);
}
