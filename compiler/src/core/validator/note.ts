import { isEmpty } from "lodash";
import { match, P } from "ts-pattern";
import { createIs } from "typia";
import type { IProperties, Note, NoteValue, Trill } from "#schema/@";

type NormalizedModifier = {
	trillValue: Trill.Value | undefined;
	noteModifier: IProperties;
};

type Normalized<T extends Note> = NormalizedModifier &
	(T extends Note.Chord
		? { type: "chord"; value: NoteValue.Chord }
		: T extends Note.Compound
			? { type: "compound"; value: (Note.Simple | Note.Chord)[] }
			: T extends Note.Quaver
				? { type: "quaver"; value: NoteValue.Quaver }
				: { type: "simple"; value: NoteValue.Simple });

export function normalize<T extends Note>(note: T): Normalized<T>;

export function normalize(note: Note): Normalized<Note> {
	if (typeof note === "string") {
		return normalizeNoteValue(note);
	}

	if (Array.isArray(note)) {
		return compound(note);
	}

	return match(note)
		.with({ note: P._ }, normalizeSimpleNote)
		.with({ chord: P._ }, ({ chord: notes, ...noteModifier }) =>
			chord(notes, noteModifier),
		)
		.with({ notes: P.string }, ({ notes, ...noteModifier }) =>
			quaver(notes, noteModifier),
		)
		.with({ notes: P.array() }, ({ notes, ...noteModifier }) =>
			compound(notes, noteModifier),
		)
		.exhaustive();
}

function normalizeNoteValue(value: NoteValue) {
	return match(value)
		.with(P.when(createIs<NoteValue.Chord>()), (value) => chord(value))
		.with(P.when(createIs<NoteValue.Quaver>()), (value) => quaver(value))
		.with(P.when(createIs<NoteValue.Simple>()), (value) => simple(value))
		.exhaustive();
}

function normalizeSimpleNote(note: Note.Simple & object): {
	type: "simple";
	value: NoteValue.Simple;
	trillValue: Trill.Value | undefined;
	noteModifier: IProperties;
} {
	if (!("trill" in note)) {
		const { note: value, ...noteModifier } = note;
		// @ts-expect-error TS wrongly complains about trill incompatibility
		return simple(value, noteModifier satisfies IProperties);
	}

	const { trill, note: value, ...noteModifier } = note;
	if (typeof trill !== "object") {
		return simple(value, noteModifier, trill);
	}

	const { value: trillValue, ...trillModifier } = trill;
	if (isEmpty(trillModifier)) {
		return simple(value, noteModifier, trillValue);
	}

	const noteModifierWithTrill = { ...noteModifier, trill: trillModifier };
	return simple(value, noteModifierWithTrill, trillValue);
}

const simple = (
	value: NoteValue.Simple,
	noteModifier: IProperties = {},
	trillValue: Trill.Value | undefined = undefined,
) => ({
	type: "simple" as const,
	value,
	noteModifier,
	trillValue,
});

const chord = (value: NoteValue.Chord, noteModifier: IProperties = {}) => ({
	type: "chord" as const,
	value,
	noteModifier,
	trillValue: undefined,
});

const quaver = (value: NoteValue.Quaver, noteModifier: IProperties = {}) => ({
	type: "quaver" as const,
	value,
	noteModifier,
	trillValue: undefined,
});

const compound = (
	value: (Note.Simple | Note.Chord)[],
	noteModifier: IProperties = {},
) => ({
	type: "compound" as const,
	value,
	noteModifier,
	trillValue: undefined,
});
