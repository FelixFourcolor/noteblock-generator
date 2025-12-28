import type { Int } from "@/types/helpers";
import type { IGlobal, IProperties, TPosition } from "../properties";
import type { FileRef } from "./ref";
import type { Notes, TValidate, Voice } from "./voice";

type VoiceGroup<T extends TValidate = TPosition> = Array<
	Voice<T, "inline"> | FileRef
>;

export type VoiceEntry<T extends TValidate = TPosition> =
	| null
	| VoiceGroup<T>
	| VoiceGroup<T>[number];

export type SongModifier<T = TPosition> = IGlobal<IProperties<T>> & {
	width?: Int<6, 16>;
};

export type Song<T extends TValidate = TPosition> =
	| (SongModifier<T> & { voices: VoiceEntry<T>[] })
	| Voice<T, "standalone">
	| Notes<T>;
