import { match, P } from "ts-pattern";
import { createEquals } from "typia";
import type {
	Deferred,
	Song,
	SongModifier,
	Voices,
} from "#lib/schema/types/components/@";
import { type ValidateError, validate } from "./validate.js";

type Validated = {
	cwd: string;
	voices: Voices;
	modifier: SongModifier;
};

export async function validateSong(
	data: Deferred<Song, { allowJson: true }>,
): Promise<Validated | ValidateError> {
	const validatedSong = await validate({
		data,
		validator: createEquals<Song>(),
	});

	return match(validatedSong)
		.with({ error: P._ }, (error) => error)
		.otherwise(({ data, cwd }) => {
			const { voices, modifier } = normalize(data);
			return { cwd, voices, modifier };
		});
}

function normalize(song: Song) {
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
