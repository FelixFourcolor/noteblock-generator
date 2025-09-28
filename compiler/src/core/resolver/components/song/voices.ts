import { UserError } from "#cli/error.js";
import type { VoiceEntry } from "#types/schema/@";
import { zipAsync } from "../generator-utils.js";
import type { Resolution, SongContext } from "../types.js";

export async function resolveVoices(
	entries: VoiceEntry[],
	ctx: SongContext,
): Promise<Resolution> {
	const THRESHOLD_TO_USE_WORKER = 6;
	const useWorker = entries.flat().length >= THRESHOLD_TO_USE_WORKER;
	const { resolveVoice } = useWorker
		? await import("../voice/voice-threaded.js")
		: await import("../voice/voice.js");

	async function merge(voices: Promise<Resolution>[]) {
		const resolutions = await Promise.all(voices);
		return {
			type: resolutions.map(({ type }) => type).includes("double")
				? ("double" as const)
				: ("single" as const),
			width: resolutions[0]!.width,
			ticks: zipAsync(resolutions.map(({ ticks }) => ticks)),
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
