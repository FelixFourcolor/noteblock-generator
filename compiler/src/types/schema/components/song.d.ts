import type { IGlobal, IProperties, TPosition } from "../properties";
import type { FileRef } from "./ref";
import type { Notes, TValidate, Voice } from "./voice";

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
