import type { tags } from "typia";
import type { Barline } from "#lib/schema/types/note/@";
import type { IProperties, TPosition } from "#lib/schema/types/properties/@";
import type { AtLeastOneOf, DistributeOmit } from "#lib/schema/types/utils/@";
import type { Deferred } from "./deferred.js";
import type { Chord, Note } from "./note.ts";

export type FutureModifier<T extends TPosition = TPosition> = AtLeastOneOf<
	DistributeOmit<IProperties<T>, "name" | "width">
>;

export type Notes<T extends TPosition = TPosition> = (
	| Barline
	| Note<T>
	| Chord<T>
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
