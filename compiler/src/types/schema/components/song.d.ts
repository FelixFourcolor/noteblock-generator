import type { Int } from "@/types/helpers";
import type { IGlobal, IProperties, TPosition } from "../properties";
import type { FileRef } from "./ref";
import type { NoteItem, TValidate, Voice } from "./voice";

type VoiceGroup<T extends TValidate = TPosition> = Array<
	Voice<T, "inline"> | FileRef
>;

export type VoiceEntry<T extends TValidate = TPosition> =
	| null
	| VoiceGroup<T>
	| VoiceGroup<T>[number];

type IWidth = { width?: Int<6, 16> };
export type SongModifier<T = TPosition> = IGlobal<IProperties<T>> & IWidth;

export type Song<T extends TValidate = TPosition> =
	| (SongModifier<T> & { voices: VoiceEntry<T>[] })
	| (IWidth & Voice<T, "standalone">)
	| NoteItem<T>[];
