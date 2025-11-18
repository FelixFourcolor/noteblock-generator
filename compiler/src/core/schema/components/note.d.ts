import type { tags } from "typia";
import type { NoteValue } from "#schema/note/@";
import type {
	INoteTrill,
	IProperties,
	IStaticProperties,
	TPosition,
} from "#schema/properties/@";
import type { DistributiveOmit, Modified, WithDoc } from "#schema/utils/@";

type RestModifier = Omit<IStaticProperties, "time">;

type NoteModifier<T extends TPosition = TPosition> = DistributiveOmit<
	IProperties<T>,
	"time" | "trill"
>;

type TrillableNoteModifier<T extends TPosition> = INoteTrill & NoteModifier<T>;

export type Note<T extends TPosition = TPosition> =
	| Note.Simple<T>
	| Note.Compound<T>
	| Note.Chord<T>
	| Note.Quaver<T>;

export namespace Note {
	export type Rest = Modified<{ note: NoteValue.Rest }, RestModifier>;

	export type Single<T extends TPosition = TPosition> = Modified<
		{ note: NoteValue.Note },
		TrillableNoteModifier<T>
	>;

	export type Simple<T extends TPosition = TPosition> = Rest | Single<T>;

	export type Chord<T extends TPosition = TPosition> = Modified<
		{ note: NoteValue.Chord },
		NoteModifier<T>
	>;

	export type Quaver<T extends TPosition = TPosition> = Modified<
		{ note: NoteValue.Quaver },
		NoteModifier<T>
	>;

	export type Compound<T extends TPosition = TPosition> = Modified<
		{ note: Compound.Value<T> },
		NoteModifier<T>
	>;
	export namespace Compound {
		export type Value<T extends TPosition = TPosition> = WithDoc<
			(Simple<T> | Chord<T> | Quaver<T>)[] & tags.MinItems<2>,
			{
				title: "Compound note";
				description: "Multiple notes played sequentially, but treated as one for the purpose of phrasing. Roughly equivalent to a glissando.";
			}
		>;
	}
}
