import type { tags } from "typia";
import type { BarLine } from "#types/schema/note/@";
import type { IProperties, TPosition } from "#types/schema/properties/@";
import type { AtLeastOneOf, DistributeOmit } from "#types/utils/@";
import type { Deferred } from "./deferred.ts";
import type { Note } from "./note.ts";

export type FutureModifier<T extends TPosition = TPosition> = AtLeastOneOf<
	DistributeOmit<IProperties<T>, "name" | "width">
>;

export type Notes<T extends TPosition = TPosition> = (
	| BarLine
	| Note<T>
	| FutureModifier<T>
)[] &
	tags.MinItems<1>;

export type VoiceModifier<T extends TPosition = TPosition> = DistributeOmit<
	IProperties<T>,
	"width"
>;

export type Voice<T extends TPosition = TPosition> = {
	notes: Deferred<Notes<T>>;
} & VoiceModifier<T>;
