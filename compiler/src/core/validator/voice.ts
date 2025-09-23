import { match, P } from "ts-pattern";
import { createEquals, is } from "typia";
import type {
	Deferred,
	Name,
	Notes,
	TPosition,
	Voice,
	VoiceModifier,
} from "#types/schema/@";
import { type ValidateError, validate } from "./validate.js";

type ValidateContext = {
	voice: Deferred<Voice>;
	cwd: string;
	index: number;
};
type Validated = {
	name: Name;
	type: TPosition;
	modifier: VoiceModifier;
	notes: Deferred<Notes>;
};

export async function validateVoice({
	voice,
	cwd,
	index,
}: ValidateContext): Promise<Validated | ValidateError> {
	const validatedVoice = await validate({
		data: voice,
		cwd,
		validator: createEquals<Voice>(),
	});
	if ("error" in validatedVoice) {
		return validatedVoice;
	}

	const {
		notes: notesRef,
		name,
		modifier,
	} = normalizeVoice({ ...validatedVoice, index });

	const validatedNotes = await validate({
		data: notesRef,
		cwd,
		validator: createEquals<Notes>(),
	});
	if ("error" in validatedNotes) {
		return validatedNotes;
	}

	const { data: notes } = validatedNotes;
	const type = resolveType({ notes, modifier });
	return { name, type, modifier, notes };
}

function normalizeVoice(args: {
	data: Voice;
	index: number;
	filename?: string;
}) {
	const { data, index, filename } = args;
	const defaultName = filename ?? `Voice ${index + 1}`;
	return match(data)
		.with({ notes: P._ }, ({ name = defaultName, notes, ...modifier }) => ({
			name,
			notes,
			modifier,
		}))
		.otherwise((notes) => ({
			name: defaultName,
			notes,
			modifier: {},
		}));
}

function resolveType(args: { notes: Notes; modifier: VoiceModifier }) {
	const { notes, modifier } = args;
	return is<Voice<"single">>({ notes, ...modifier })
		? ("single" as const)
		: ("double" as const);
}
