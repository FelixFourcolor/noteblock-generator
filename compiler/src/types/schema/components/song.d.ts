import type { tags } from "typia";
import type { IGlobalProperties, TPosition } from "#types/schema/properties/@";
import type { Deferred } from "./deferred.ts";
import type { Notes, Voice } from "./voice.ts";

type VoiceGroup<T extends TPosition = TPosition> = Deferred<Voice<T>>[] &
	tags.MinItems<2>;

export type VoiceEntry<T extends TPosition = TPosition> =
	| null
	| Deferred<Voice<T>>
	| VoiceGroup<T>;

export type Voices<T extends TPosition = TPosition> = VoiceEntry<T>[] &
	tags.MinItems<1>;

export type SongModifier<T extends TPosition = TPosition> =
	IGlobalProperties<T>;

export type Song<T extends TPosition = TPosition> =
	| ({ voices: Voices<T> } & SongModifier<T>)
	| Voice<T>
	| Notes<T>;
