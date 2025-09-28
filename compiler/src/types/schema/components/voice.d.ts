import type { tags } from "typia";
import type { BarLine } from "#schema/note/@";
import type { IGlobal, IProperties, TPosition } from "#schema/properties/@";
import type { AtLeastOneOf } from "#utils/@";
import type { Deferred } from "./deferred.ts";
import type { Note } from "./note.ts";

export type FutureModifier<T extends TPosition = TPosition> = AtLeastOneOf<
	IProperties<T>
>;

export type Notes<T extends TPosition = TPosition> = (
	| BarLine
	| Note<T>
	| FutureModifier<T>
)[] &
	tags.MinItems<1>;

export type Voice<T extends TPosition = TPosition> = IGlobal<IProperties<T>> & {
	notes: Deferred<Notes<T>>;
};
