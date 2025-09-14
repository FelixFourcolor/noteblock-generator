import type { tags } from "typia";
import type { NoteValue } from "#lib/schema/types/note/@";
import type {
	IProperties,
	ITrillNote,
	TPosition,
} from "#lib/schema/types/properties/@";
import type { DistributeOmit, OneOf } from "#lib/schema/types/utils/@";

type RestModifier<T extends TPosition> = Pick<IProperties<T>, "delay" | "beat">;

type MultiNoteModifier<T extends TPosition> = DistributeOmit<
	IProperties<T>,
	"trill" | "width" | "name" | "time"
>;

type SingleNoteModifier<T extends TPosition> = ITrillNote &
	MultiNoteModifier<T>;

type Modified<
	P extends {
		name: string;
		modifier: object;
		type: unknown;
	},
> =
	| P["type"]
	| (OneOf<{ [K in string & P["name"]]: P["type"] }> & P["modifier"]);

export namespace Note {
	export type Rest<T extends TPosition = TPosition> = Modified<{
		name: "note";
		type: NoteValue.Rest;
		modifier: RestModifier<T>;
	}>;
	export type Single<T extends TPosition = TPosition> = Modified<{
		name: "note";
		type: NoteValue.Single;
		modifier: SingleNoteModifier<T>;
	}>;
	export type Compound<T extends TPosition = TPosition> = Modified<{
		name: "note";
		type: NoteValue.Compound;
		modifier: MultiNoteModifier<T>;
	}>;
	export type Continuous<T extends TPosition = TPosition> = Modified<{
		name: "note";
		type: NoteValue.Continuous;
		modifier: MultiNoteModifier<T>;
	}>;
	export type Sequential<T extends TPosition = TPosition> = Modified<{
		name: "note";
		type: NoteValue.Sequential;
		modifier: MultiNoteModifier<T>;
	}>;
	export type Parallel<T extends TPosition = TPosition> = Modified<{
		name: "note";
		type: NoteValue.Parallel;
		modifier: MultiNoteModifier<T>;
	}>;
}

export type Note<T extends TPosition = TPosition> =
	| Note.Rest<T>
	| Note.Single<T>
	| Note.Compound<T>
	| Note.Continuous<T>
	| Note.Sequential<T>
	| Note.Parallel<T>;

export type Chord<T extends TPosition = TPosition> = Modified<{
	name: "note";
	type: Note<T>[] & tags.MinItems<2>;
	modifier: MultiNoteModifier<T>;
}>;
