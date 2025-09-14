import { match, P } from "ts-pattern";
import {
	type Deferred,
	type IProperties,
	Song,
	type Voices,
} from "#lib/new-schema/@";
import { type ValidateError, validate } from "./validate.js";

type Validated = {
	cwd: string;
	voices: Voices;
	modifier: IProperties;
};

export async function validateSong(
	data: Deferred<Song>,
): Promise<Validated | ValidateError> {
	const validatedSong = await validate({
		data,
		validator: Song(),
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
