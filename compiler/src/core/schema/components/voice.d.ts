import type { BarLine } from "#schema/note/@";
import type { IGlobal, IProperties, TPosition } from "#schema/properties/@";
import type { Deferred } from "./deferred.ts";
import type { Note } from "./note.ts";

export type TValidate = TPosition | "lazy";

export type Notes<T extends TValidate = TPosition> = (T extends TPosition
	? BarLine | Note<T> | IProperties<T>
	: unknown)[];

export type Voice<T extends TValidate = TPosition> = IGlobal<IProperties<T>> & {
	notes: Deferred<Notes<T>>;
};
