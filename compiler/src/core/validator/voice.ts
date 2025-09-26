import { createEquals, is } from "typia";
import type {
	Deferred,
	Name,
	Notes,
	TPosition,
	Voice,
	VoiceModifier,
} from "#types/schema/@";
import { type Validated, type ValidateError, validate } from "./validate.js";

type ValidateContext = {
	voice: Deferred<Voice>;
	cwd: string;
	index: number;
};
type ValidatedVoice = {
	name: Name;
	type: TPosition;
	modifier: VoiceModifier;
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
		name: name ?? filename ?? `Voice ${index + 1}`,
		type,
		modifier,
		notes,
	};
}

function normalize(voice: Validated<Voice>) {
	const { data, filename } = voice;
	const { name = filename, notes, ...modifier } = data;
	return { name, notes, modifier };
}

function resolveType(args: { notes: Notes; modifier: VoiceModifier }) {
	const { notes, modifier } = args;
	return is<Voice<"single">>({ notes, ...modifier })
		? ("single" as const)
		: ("double" as const);
}
