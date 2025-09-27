import type { tags } from "typia";
import type { BarLine } from "#types/schema/note/@";
import type {
	IName,
	IPositionalProperties,
	TPosition,
} from "#types/schema/properties/@";
import type { AtLeastOneOf } from "#types/utils/@";
import type { Deferred } from "./deferred.ts";
import type { Note } from "./note.ts";

export type FutureModifier<T extends TPosition = TPosition> = AtLeastOneOf<
	IPositionalProperties<T>
>;

export type Notes<T extends TPosition = TPosition> = (
	| BarLine
	| Note<T>
	| FutureModifier<T>
)[] &
	tags.MinItems<1>;

export type VoiceModifier<T extends TPosition = TPosition> =
	IPositionalProperties<T> & Partial<IName>;

export type Voice<T extends TPosition = TPosition> = {
	notes: Deferred<Notes<T>>;
} & VoiceModifier<T>;
