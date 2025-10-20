import { UserError } from "#cli/error.js";
import type { VoiceEntry } from "#schema/@";
import { zip } from "../generator-utils.js";
import type { SongContext, VoiceResolution } from "../resolution.js";
import { resolveVoice } from "../voice/voice.js";

export async function resolveVoices(
	entries: VoiceEntry[],
	ctx: SongContext,
): Promise<VoiceResolution> {
	async function merge(voices: Promise<VoiceResolution>[]) {
		const VoiceResolutions = await Promise.all(voices);
		return {
			type: VoiceResolutions.map(({ type }) => type).includes("double")
				? ("double" as const)
				: ("single" as const),
			time: VoiceResolutions[0]!.time,
			ticks: zip(VoiceResolutions.map(({ ticks }) => ticks)),
		};
	}

	const voices = entries
		.reverse()
		.map((entry, index) => {
			if (entry === null) {
				return null;
			}
			if (!Array.isArray(entry)) {
				return resolveVoice(entry, { ...ctx, index });
			}
			return merge(
				entry.map((subvoice, subIndex) => {
					return resolveVoice(subvoice, { ...ctx, index: [index, subIndex] });
				}),
			);
		})
		.filter((e) => e !== null);

	if (voices.length === 0) {
		throw new UserError("Song must contain at least one voice.");
	}

	return merge(voices);
}
