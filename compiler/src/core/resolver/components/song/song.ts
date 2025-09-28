import { is } from "typia";
import { UserError } from "#cli/error.js";
import { validateSong } from "#core/validator/@";
import type { Deferred, Song, SongModifier } from "#types/schema/@";
import type { Resolution } from "../types.js";
import { resolveVoices } from "./voices.js";

export async function resolveSong(
	song: Deferred<Song, { allowJson: true }>,
): Promise<Resolution> {
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
		if (!is<SongModifier<"single">>(songModifier)) {
			type = "double";
		}
	}

	return { ...voicesResolution, type };
}
