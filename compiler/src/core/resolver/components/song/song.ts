import { is } from "typia";
import { UserError } from "#cli/error.js";
import { Time } from "#core/resolver/properties/@";
import { validateSong } from "#core/validator/@";
import type { Deferred, Song, SongModifier, TPosition } from "#types/schema/@";
import type { Resolution, SongResolution } from "../types.js";
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
	const width = resolveWidth(songModifier);
	const type = resolveType({ songModifier, voicesResolution });

	return { ...voicesResolution, width, type };
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
	voicesResolution: Resolution;
}): TPosition {
	if (voicesType === "double") {
		return "double";
	}
	return is<SongModifier<"single">>(songModifier) ? "single" : "double";
}
