import { is } from "typia";
import { UserError } from "#cli/error.js";
import { Time } from "#lib/resolver/properties/@";
import type {
	Deferred,
	Song,
	SongModifier,
	TPosition,
	VoiceEntry,
} from "#lib/schema/types/@";
import { validateSong } from "#lib/schema/validator/@";
import { zipAsync } from "./generator-utils.js";
import type { VoiceResolution } from "./voice.js";

export interface SongResolution extends VoiceResolution {
	width: number;
}

export async function resolveSong(
	song: Deferred<Song, { allowJson: true }>,
): Promise<SongResolution> {
	const validated = await validateSong(song);
	if ("error" in validated) {
		throw new UserError(validated.error);
	}
	const { voices, modifier: songModifier, cwd } = validated;

	const voicesResolution = await resolveVoices(voices, { songModifier, cwd });
	const width = resolveWidth(songModifier);
	const type = resolveType({ songModifier, voicesResolution });
	return { ...voicesResolution, width, type };
}

export type SongContext = {
	songModifier: SongModifier;
	cwd: string;
};

export async function resolveVoices(
	entries: VoiceEntry[],
	ctx: SongContext,
): Promise<VoiceResolution> {
	const THRESHOLD_TO_USE_WORKER = 8;
	const useWorker = entries.flat().length >= THRESHOLD_TO_USE_WORKER;
	const { resolveVoice } = useWorker
		? await import("./voice-threaded.js")
		: await import("./voice.js");

	async function merge(promises: Promise<VoiceResolution>[]) {
		const voices = await Promise.all(promises);
		const type = voices.map(({ type }) => type).includes("double")
			? ("double" as const)
			: ("single" as const);
		const ticks = zipAsync(voices.map(({ ticks }) => ticks));
		return { type, ticks };
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

function resolveWidth({ time, width }: SongModifier) {
	if (width) {
		return width;
	}
	const resolvedTime = new Time().transform(time).resolve();
	for (let candidate = 16; candidate >= 8; candidate--) {
		if (resolvedTime % candidate === 0) {
			return candidate;
		}
	}
	return 16;
}

function resolveType({
	songModifier,
	voicesResolution: { type: voicesType },
}: {
	songModifier: SongModifier;
	voicesResolution: VoiceResolution;
}): TPosition {
	if (voicesType === "double") {
		return "double";
	}
	return is<SongModifier<"single">>(songModifier) ? "single" : "double";
}
