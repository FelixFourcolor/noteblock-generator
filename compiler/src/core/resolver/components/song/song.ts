import { is } from "typia";
import { UserError } from "#cli/error.js";
import { validateSong } from "#core/validator/@";
import type { Deferred, IProperties, Song, Time, TPosition } from "#schema/@";
import type { SongResolution } from "../resolution.js";
import { resolveVoices } from "./voices.js";

export async function resolveSong(
	song: Deferred<Song, { allowJson: true }>,
): Promise<SongResolution> {
	const validated = await validateSong(song);
	if ("error" in validated) {
		throw new UserError(validated.error);
	}

	const { voices, modifier: songModifier, cwd } = validated;
	const voicesResolution = await resolveVoices(voices, { songModifier, cwd });

	let { type } = voicesResolution;
	if (type === "single") {
		// Must check "is not single" instead of "is double"
		// because single extends double
		if (!is<IProperties<"single">>(songModifier)) {
			type = "double";
		}
	}

	const { time: voiceTime, ticks } = voicesResolution;
	let { time } = songModifier;
	if (typeof time !== "number") {
		time = voiceTime;
	}
	const width = resolveWidth({ time, type });

	return { width, type, ticks };
}

function resolveWidth({ time, type }: { time: Time; type: TPosition }) {
	const min = 8;
	const max = type === "single" ? 16 : 12;
	const middle = 12;

	if (min <= time && time <= max) {
		return time;
	}

	for (let candidate = middle; candidate <= max; candidate++) {
		if (time % candidate === 0) {
			return candidate;
		}
	}
	for (let candidate = middle - 1; candidate >= min; candidate--) {
		if (time % candidate === 0) {
			return candidate;
		}
	}

	return max;
}
