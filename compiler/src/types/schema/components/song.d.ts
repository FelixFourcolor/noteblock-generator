import type { tags } from "typia";
import type { IGlobal, IProperties, TPosition } from "#schema/properties/@";
import type { FileRef } from "./ref.js";
import type { Notes, TValidate, Voice } from "./voice.ts";

type VoiceGroup<T extends TValidate = TPosition> = (Voice<T> | FileRef)[] &
	tags.MinItems<1>;

export type VoiceEntry<T extends TValidate = TPosition> =
	| null
	| (Voice<T> | FileRef)
	| VoiceGroup<T>;

export type Voices<T extends TValidate = TPosition> = VoiceEntry<T>[] &
	tags.MinItems<1>;

export type Song<T extends TValidate = TPosition> =
	| (IGlobal<IProperties<T>> & { voices: Voices<T> })
	| Voice<T>
	| Notes<T>;
