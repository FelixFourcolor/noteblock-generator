import { isEmpty } from "lodash";
import { is } from "typia";
import type { IProperties, Note, NoteValue, Trill } from "#schema/@";

type NormalizedModifier = {
	trillValue?: Trill.Value | undefined;
	noteModifier: IProperties;
};

type Normalized<T extends Note> = NormalizedModifier &
	(T extends Note.Chord
		? { type: "chord"; value: (Note.Single | Note.Compound)[] }
		: T extends Note.Compound
			? { type: "compound"; value: Note.Simple[] }
			: { type: "simple"; value: NoteValue });

export function normalize<T extends Note>(note: T): Normalized<T>;
export function normalize(note: Note): Normalized<Note> {
	if (typeof note === "string") {
		return simple(note);
	}

	if (Array.isArray(note)) {
		if (is<[NoteValue[]]>(note)) {
			return chord(note);
		}
		return compound(note);
	}

	if ("notes" in note) {
		const { notes: value, ...noteModifier } = note;
		return compound(value, noteModifier);
	}

	if ("chord" in note) {
		const { chord: chordItems, ...noteModifier } = note;
		return chord(chordItems, noteModifier);
	}

	if (!("trill" in note)) {
		const { note: value, ...noteModifier } = note;
		return simple(value, noteModifier as IProperties);
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

function simple(
	value: NoteValue,
	noteModifier: IProperties = {},
	trillValue: Trill.Value | undefined = undefined,
): Normalized<Note.Simple> {
	return { type: "simple", value, noteModifier, trillValue };
}

function compound(
	value: Note.Simple[],
	noteModifier: IProperties = {},
): Normalized<Note.Compound> {
	return { type: "compound", value, noteModifier };
}

function chord(
	value: (Note.Single | Note.Compound)[],
	noteModifier: IProperties = {},
): Normalized<Note.Chord> {
	return { type: "chord", value, noteModifier };
}
