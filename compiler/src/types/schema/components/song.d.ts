import type { tags } from "typia";
import type { IGlobal, IProperties, TPosition } from "#schema/properties/@";
import type { FileRef } from "./ref.js";
import type { Notes, TValidate, Voice } from "./voice.ts";

type VoiceGroup<T extends TValidate = TPosition> = (
	| Voice<T, "inline">
	| FileRef
)[];

export type VoiceEntry<T extends TValidate = TPosition> =
	| null
	| VoiceGroup<T>
	| VoiceGroup<T>[number];

export type Song<T extends TValidate = TPosition> =
	| (IGlobal<IProperties<T>> & { voices: VoiceEntry<T>[] })
	| Voice<T, "standalone">
	| Notes<T>;
