import { match, P } from "ts-pattern";
import { createEquals, is } from "typia";
import { UserError } from "#cli/error.js";
import type {
	FileRef,
	IProperties,
	Song,
	Time,
	TPosition,
	Voices,
} from "#schema/@";
import type { ResolverCache } from "../cache.js";
import type { Tick } from "./tick.js";
import { type ValidateError, validate } from "./utils/validate.js";
import { resolveVoices } from "./voices.js";

export type JsonString = `json://${string}`;

export type SongResolution<T extends TPosition = TPosition> = {
	type: T;
	width: number;
	ticks: Iterable<Tick>;
};

export async function resolveSong(
	song: FileRef | JsonString,
	cache?: ResolverCache,
): Promise<SongResolution> {
	const validated = await validateSong(song);
	if ("error" in validated) {
		throw new UserError(validated.error);
	}

	const { voices, modifier: songModifier, cwd } = validated;
	const context = { songModifier, cwd };
	const voicesResolution = await resolveVoices(voices, context, cache);

	let { type } = voicesResolution;
	if (type === "single") {
		// Must check "is not single" instead of "is double",
		// because single is a subset of double
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

type ValidatedSong = {
	cwd: string;
	voices: Voices;
	modifier: IProperties;
};

async function validateSong(
	data: FileRef | JsonString,
): Promise<ValidatedSong | ValidateError> {
	const validatedSong = await validate(data, createEquals<Song>());

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
