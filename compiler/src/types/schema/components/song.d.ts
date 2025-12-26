import type { Int } from "@/types/helpers";
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

export type ISongProperties<T = TPosition> = IGlobal<IProperties<T>> & {
	width?: Int<8, 16>;
};

export type Song<T extends TValidate = TPosition> =
	| (ISongProperties<T> & { voices: VoiceEntry<T>[] })
	| Voice<T, "standalone">
	| Notes<T>;
