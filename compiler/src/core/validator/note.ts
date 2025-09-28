import { isEmpty } from "lodash";
import { is } from "typia";
import type {
	IGlobalProperties,
	IStatic,
	Note,
	NoteValue,
	Trill,
} from "#types/schema/@";

type NormalizedModifier = {
	trillValue?: Trill.Value | undefined;
	noteModifier: IGlobalProperties;
};

type Normalized<T extends Note> = NormalizedModifier &
	(T extends Note.Chord
		? { type: "chord"; value: Note.Chord.Item[] }
		: T extends Note.Compound
			? { type: "compound"; value: NoteValue[] }
			: { type: "simple"; value: NoteValue });

export function normalize(note: Note): Normalized<Note> {
	if (typeof note === "string") {
		return simple(note);
	}

	if (Array.isArray(note)) {
		if (is<string[]>(note)) {
			return compound(note);
		}
		return chord(note);
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
		return simple(value, noteModifier as IGlobalProperties);
	}

	const { trill, note: value, ...noteModifier } = note;
	if (typeof trill !== "object") {
		return simple(value, noteModifier, trill);
	}

	const { value: trillValue, ...trillModifier } = trill;
	if (isEmpty(trillModifier)) {
		return simple(value, noteModifier, trillValue);
	}

	const noteModifierWithTrill = {
		...noteModifier,
		// isEmpty check above => IStatic satisfies here
		trill: trillModifier as IStatic<Trill>,
	};
	return simple(value, noteModifierWithTrill, trillValue);
}

function simple(
	value: NoteValue,
	noteModifier: IGlobalProperties = {},
	trillValue: Trill.Value | undefined = undefined,
): Normalized<Note.Simple> {
	return { type: "simple", value, noteModifier, trillValue };
}

function compound(
	value: NoteValue[],
	noteModifier: IGlobalProperties = {},
): Normalized<Note.Compound> {
	return { type: "compound", value, noteModifier };
}

function chord(
	value: Note.Chord.Item[],
	noteModifier: IGlobalProperties = {},
): Normalized<Note.Chord> {
	return { type: "chord", value, noteModifier };
}
