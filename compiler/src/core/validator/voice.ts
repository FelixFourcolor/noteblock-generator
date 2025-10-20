import { createEquals, equals } from "typia";
import type { Deferred, IProperties, Notes, TPosition, Voice } from "#schema/@";
import { type Validated, type ValidateError, validate } from "./validate.js";

type ValidateContext = {
	voice: Deferred<Voice<"lazy">>;
	cwd: string;
	index: number | [number, number];
};
type ValidatedVoice = {
	name: string;
	type: TPosition;
	modifier: IProperties;
	notes: Notes<"lazy">;
};

export async function validateVoice({
	voice,
	cwd,
	index,
}: ValidateContext): Promise<ValidatedVoice | ValidateError> {
	const validatedVoice = await validate({
		data: voice,
		cwd,
		validator: createEquals<Voice<"lazy">>(),
	});

	if ("error" in validatedVoice) {
		return validatedVoice;
	}

	const { notes: notesRef, name, modifier } = normalize(validatedVoice);

	const validatedNotes = await validate({
		data: notesRef,
		cwd,
		validator: createEquals<Notes<"lazy">>(),
	});

	if ("error" in validatedNotes) {
		return validatedNotes;
	}

	const { data: notes, filename } = validatedNotes;
	const type = resolveType({ notes, modifier });
	return {
		name: name ?? filename ?? `Voice ${index}`,
		type,
		modifier,
		notes,
	};
}

function normalize(voice: Validated<Voice<"lazy">>) {
	const { data, filename } = voice;
	const { notes, ...modifier } = data;
	return { name: filename, notes, modifier };
}

function resolveType(args: { notes: unknown[]; modifier: IProperties }) {
	const { notes, modifier } = args;
	return equals<Voice<"single">>({ notes, ...modifier })
		? ("single" as const)
		: ("double" as const);
}
