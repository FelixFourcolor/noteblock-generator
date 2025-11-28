import { basename } from "node:path";
import { createEquals, equals, is } from "typia";
import type {
	FileRef,
	IProperties,
	Notes,
	Time,
	TPosition,
	Voice,
} from "#schema/@";
import { resolveNotes } from "./notes.js";
import type { Tick } from "./tick.js";
import { Context } from "./utils/context.js";
import { type ValidateError, validate } from "./utils/validate.js";
import type { SongContext } from "./voices.js";

export type VoiceContext = SongContext & {
	index: number | [number, number];
};

export type VoiceResolution = {
	type: TPosition;
	ticks: Generator<Tick>;
	time: Time;
};

export async function resolveVoice(
	voice: Voice<"lazy"> | FileRef,
	ctx: VoiceContext,
): Promise<VoiceResolution> {
	const { songModifier, index } = ctx;
	const fallbackName = `Voice ${index}`;

	const validated = await validateVoice(voice, ctx);
	if ("error" in validated) {
		const name = "context" in validated ? validated.context.name : fallbackName;
		return {
			time: NaN,
			type: "single",
			ticks: (function* () {
				yield [
					{
						error: validated.error,
						voice: name,
						measure: { bar: 1, tick: 1 },
					},
				];
			})(),
		};
	}
	const { type, notes, modifier, name = fallbackName } = validated;

	const level = typeof index === "number" ? index : index[0];
	const context = new Context(name)
		.transform({ level })
		.transform(songModifier)
		.fork(modifier);

	const { time } = context.resolveStatic();
	return { time, type, ticks: resolveNotes(notes, context) };
}

type ValidatedVoice = {
	name: string | undefined;
	type: TPosition;
	modifier: IProperties;
	notes: Notes<"lazy">;
};

async function validateVoice(
	voice: Voice<"lazy"> | FileRef,
	{ cwd }: Pick<VoiceContext, "cwd">,
): Promise<ValidatedVoice | ValidateError<{ name: string }>> {
	const inferredName = inferName(voice);

	const validateVoiceResult = await validate(
		voice,
		createEquals<Voice<"lazy">>(),
		cwd,
	);
	if ("error" in validateVoiceResult) {
		const { error } = validateVoiceResult;
		if (!inferredName) {
			return { error };
		}
		return { error, context: { name: inferredName } };
	}

	const {
		data: { notes: notesRef, ...modifier },
		filename: voiceFileName,
	} = validateVoiceResult;
	const validateNotesResult = await validate(
		notesRef,
		createEquals<Notes<"lazy">>(),
		cwd,
	);
	if ("error" in validateNotesResult) {
		const { error } = validateNotesResult;
		const name = voiceFileName ?? inferredName;
		if (!name) {
			return { error };
		}
		return { error, context: { name } };
	}
	const { data: notes, filename: notesFileName } = validateNotesResult;

	const name = voiceFileName ?? notesFileName ?? inferredName;
	const type = resolveType({ notes, modifier });
	return { name, type, modifier, notes };
}

function inferName(voice: unknown | FileRef) {
	if (is<FileRef>(voice)) {
		return basename(voice.slice("file://".length), ".yaml");
	}
	if (typeof voice === "object" && voice !== null && "notes" in voice) {
		return inferName(voice.notes);
	}
	return undefined;
}

function resolveType(args: { notes: unknown[]; modifier: IProperties }) {
	const { notes, modifier } = args;
	return equals<Voice<"single">>({ notes, ...modifier })
		? ("single" as const)
		: ("double" as const);
}
