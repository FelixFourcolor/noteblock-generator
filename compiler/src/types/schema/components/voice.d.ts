import type { tags } from "typia";
import type { BarLine } from "#schema/note/@";
import type { IGlobal, IProperties, TPosition } from "#schema/properties/@";
import type { Deferred } from "./deferred.ts";
import type { Note } from "./note.ts";

export type Notes<T extends TPosition = TPosition> = (
	| BarLine
	| Note<T>
	| IProperties<T>
)[] &
	tags.MinItems<1>;

export type Voice<T extends TPosition = TPosition> = IGlobal<IProperties<T>> & {
	notes: Deferred<Notes<T>>;
};
