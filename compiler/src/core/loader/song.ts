import { match, P } from "ts-pattern";
import { createIs } from "typia";
import type { FileRef, Song } from "#schema/@";
import type { JsonString, LoadedSong } from "./types.js";
import { type ValidateError, validate } from "./validate.js";
import { loadVoice } from "./voice.js";

export async function loadSong(
	data: FileRef | JsonString,
): Promise<LoadedSong | ValidateError> {
	const validateResult = await validate(data, createIs<Song<"lazy">>());

	return match(validateResult)
		.with({ error: P._ }, (error) => error)
		.otherwise(({ validated, cwd }) => {
			const { voices, modifier } = normalize(validated);
			return {
				voices: voices.map((voice) =>
					match(voice)
						.with(null, () => null)
						.with(P.array(), (group) => group.map((v) => loadVoice(v, cwd)))
						.otherwise((v) => loadVoice(v, cwd)),
				),
				modifier,
			};
		});
}

function normalize(song: Song<"lazy">) {
	return match(song)
		.with({ voices: P._ }, ({ voices, ...modifier }) => ({
			voices,
			modifier,
		}))
		.with({ notes: P._ }, (voice) => ({
			voices: [voice],
			modifier: {},
		}))
		.otherwise((notes) => ({
			voices: [{ notes }],
			modifier: {},
		}));
}
