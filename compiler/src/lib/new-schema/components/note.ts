import { type Type, type } from "arktype";
import { Modified } from "../modified.js";
import { NoteValue } from "../note/note-value.js";
import type { TPosition } from "../properties/positional/position.js";
import { IProperties } from "../properties/properties.js";
import { INoteTrill } from "../properties/static/trill.js";

const RestModifier = IProperties().pick("delay", "beat");

type MultiNoteModifier<T extends TPosition> = Omit<
	IProperties<T>,
	"trill" | "time" | "width" | "name"
>;

function MultiNoteModifier<T extends TPosition>(t?: T) {
	return IProperties(t as TPosition | undefined).omit(
		"trill",
		"time",
		"width",
		"name",
	) as Type<MultiNoteModifier<T>>;
}

type SingleNoteModifier<T extends TPosition> = INoteTrill &
	MultiNoteModifier<T>;

function SingleNoteModifier<T extends TPosition>(t?: T) {
	return type.and(
		MultiNoteModifier(t as TPosition | undefined),
		INoteTrill,
	) as unknown as Type<SingleNoteModifier<T>>;
}

const Rest = Modified({ rest: NoteValue.Rest }, RestModifier);

function Single<T extends TPosition>(t?: T) {
	return Modified(
		{ note: NoteValue.Single },
		SingleNoteModifier(t as TPosition | undefined),
	) as unknown as Type<Note.Single<T>>;
}

function Compound<T extends TPosition>(t?: T) {
	return Modified(
		{ note: NoteValue.Compound },
		MultiNoteModifier(t as TPosition | undefined),
	) as unknown as Type<Note.Compound<T>>;
}

function Continuous<T extends TPosition>(t?: T) {
	return Modified(
		{ note: NoteValue.Continuous },
		MultiNoteModifier(t as TPosition | undefined),
	) as unknown as Type<Note.Continuous<T>>;
}

function Sequential<T extends TPosition>(t?: T) {
	return Modified(
		{ note: NoteValue.Sequential },
		MultiNoteModifier(t as TPosition | undefined),
	) as unknown as Type<Note.Sequential<T>>;
}

function Parallel<T extends TPosition>(t?: T) {
	return Modified(
		{ note: NoteValue.Parallel },
		MultiNoteModifier(t as TPosition | undefined),
	) as unknown as Type<Note.Parallel<T>>;
}

export function Note<T extends TPosition = TPosition>(t?: T) {
	const T = t as TPosition | undefined;
	const Note = type.or(
		Rest,
		Single(T),
		Compound(T),
		Continuous(T),
		Sequential(T),
		Parallel(T),
	) as unknown as Type<Note<T>>;
	return Object.assign(Note, {
		Rest,
		Single: Single(T) as Type<Note.Single<T>>,
		Compound: Compound(T) as Type<Note.Compound<T>>,
		Continuous: Continuous(T) as Type<Note.Continuous<T>>,
		Sequential: Sequential(T) as Type<Note.Sequential<T>>,
		Parallel: Parallel(T) as Type<Note.Parallel<T>>,
	});
}

export function Chord<T extends TPosition = TPosition>(t?: T) {
	return Modified(
		{ note: Note(t).array().atLeastLength(2) },
		MultiNoteModifier(t),
	) as Type<Chord<T>>;
}

export type Chord<T extends TPosition = TPosition> = Modified<
	{ note: Type<Note<T>[]> },
	Type<MultiNoteModifier<T>>
>;

export type Note<T extends TPosition = TPosition> =
	| Note.Rest
	| Note.Single<T>
	| Note.Compound<T>
	| Note.Continuous<T>
	| Note.Sequential<T>
	| Note.Parallel<T>;

export namespace Note {
	export type Rest = typeof Rest.t;
	export type Single<T extends TPosition> = Modified<
		{ note: typeof NoteValue.Single },
		Type<SingleNoteModifier<T>>
	>;
	export type Compound<T extends TPosition> = Modified<
		{ note: typeof NoteValue.Compound },
		Type<MultiNoteModifier<T>>
	>;
	export type Continuous<T extends TPosition> = Modified<
		{ note: typeof NoteValue.Continuous },
		Type<MultiNoteModifier<T>>
	>;
	export type Sequential<T extends TPosition> = Modified<
		{ note: typeof NoteValue.Sequential },
		Type<MultiNoteModifier<T>>
	>;
	export type Parallel<T extends TPosition> = Modified<
		{ note: typeof NoteValue.Parallel },
		Type<MultiNoteModifier<T>>
	>;
}
