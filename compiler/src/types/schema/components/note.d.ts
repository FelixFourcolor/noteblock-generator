import type { tags } from "typia";
import type { NoteValue } from "#types/schema/note/@";
import type {
	INoteTrill,
	IProperties,
	TPosition,
} from "#types/schema/properties/@";
import type { DistributeOmit, Modified } from "#types/utils/@";

type RestModifier<T extends TPosition> = Pick<IProperties<T>, "delay" | "beat">;

type NoteModifier<T extends TPosition> = INoteTrill & MultiNoteModifier<T>;

type MultiNoteModifier<T extends TPosition> = DistributeOmit<
	IProperties<T>,
	"trill" | "width" | "name" | "time"
>;

export type Note<T extends TPosition = TPosition> =
	| Note.Simple<T>
	| Note.Compound<T>
	| Note.Chord<T>;

export namespace Note {
	export type Rest<T extends TPosition = TPosition> = Modified<
		{ note: NoteValue.Rest },
		RestModifier<T>
	>;

	export type Single<T extends TPosition = TPosition> = Modified<
		{ note: NoteValue.Note },
		NoteModifier<T>
	>;

	export type Simple<T extends TPosition = TPosition> = Rest<T> | Single<T>;

	export type Compound<T extends TPosition = TPosition> = Modified<
		{ notes: NoteValue[] & tags.MinItems<2> },
		MultiNoteModifier<T>
	>;

	export type Chord<T extends TPosition = TPosition> =
		| ([NoteValue][] & tags.MinItems<2>)
		| ({ chord: Chord.Item<T>[] & tags.MinItems<2> } & MultiNoteModifier<T>);

	export namespace Chord {
		export type Item<T extends TPosition = TPosition> =
			| Note.Single<T>
			| Note.Compound<T>;
	}
}
