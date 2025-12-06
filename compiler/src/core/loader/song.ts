import { match, P } from "ts-pattern";
import { createIs } from "typia";
import { UserError } from "@/cli/error";
import type { FileRef, Song } from "@/types/schema";
import type { JsonString, LoadedSong } from "./types";
import { validate } from "./validate";
import { loadVoice } from "./voice";

export async function loadSong(
	data: FileRef | JsonString,
): Promise<LoadedSong> {
	return match(await validate(data, createIs<Song<"lazy">>()))
		.with({ error: P.select() }, (error) => {
			throw new UserError(error);
		})
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
