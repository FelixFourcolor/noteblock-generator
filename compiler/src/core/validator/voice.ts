import { createEquals, equals } from "typia";
import type { Deferred, IProperties, Notes, TPosition, Voice } from "#schema/@";
import { type Validated, type ValidateError, validate } from "./validate.js";

type ValidateContext = {
	voice: Deferred<Voice>;
	cwd: string;
	index: number;
};
type ValidatedVoice = {
	name: string;
	type: TPosition;
	modifier: IProperties;
	notes: Notes;
};

export async function validateVoice({
	voice,
	cwd,
	index,
}: ValidateContext): Promise<ValidatedVoice | ValidateError> {
	const validatedVoice = await validate({
		data: voice,
		cwd,
		validator: createEquals<Voice>(),
	});

	if ("error" in validatedVoice) {
		return validatedVoice;
	}

	const { notes: notesRef, name, modifier } = normalize(validatedVoice);

	const validatedNotes = await validate({
		data: notesRef,
		cwd,
		validator: createEquals<Notes>(),
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

function normalize(voice: Validated<Voice>) {
	const { data, filename } = voice;
	const { notes, ...modifier } = data;
	return { name: filename, notes, modifier };
}

function resolveType(args: { notes: Notes; modifier: IProperties }) {
	const { notes, modifier } = args;
	return equals<Voice<"single">>({ notes, ...modifier })
		? ("single" as const)
		: ("double" as const);
}
