import type { tags } from "typia";
import type { NoteValue } from "#schema/note/@";
import type {
	INoteTrill,
	IProperties,
	IStaticProperties,
	TPosition,
} from "#schema/properties/@";
import type { DistributiveOmit, Modified } from "#utils/@";

type RestModifier = Omit<IStaticProperties, "time">;

type MultiNoteModifier<T extends TPosition> = DistributiveOmit<
	IProperties<T>,
	"time" | "trill"
>;

type NoteModifier<T extends TPosition> = INoteTrill & MultiNoteModifier<T>;

export type Note<T extends TPosition = TPosition> =
	| Note.Simple<T>
	| Note.Compound<T>
	| Note.Chord<T>;

export namespace Note {
	export type Rest = Modified<{ note: NoteValue.Rest }, RestModifier>;

	export type Single<T extends TPosition = TPosition> = Modified<
		{ note: NoteValue.Note },
		NoteModifier<T>
	>;

	export type Simple<T extends TPosition = TPosition> = Rest | Single<T>;

	export type Compound<T extends TPosition = TPosition> = Modified<
		{ notes: Simple<T>[] & tags.MinItems<2> },
		MultiNoteModifier<T>
	>;

	export type Chord<T extends TPosition = TPosition> =
		| [NoteValue[] & tags.MinItems<2>]
		| ({
				chord: (Single<T> | Compound<T>)[] & tags.MinItems<2>;
		  } & MultiNoteModifier<T>);
}
