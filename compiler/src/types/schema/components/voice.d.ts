import type { Modified } from "@/types/helpers";
import type { BarLine } from "@/types/schema/note";
import type { IGlobal, IProperties, PresetId, TPosition } from "../properties";
import type { Note } from "./note";
import type { FileRef } from "./ref";

export type TValidate = TPosition | "lazy";

export type VoiceModifier<T = TPosition> = IGlobal<IProperties<T>>;
export type FutureModifier<T = TPosition> = IProperties<T> | PresetId;

export type NoteItem<T extends TValidate = TPosition> = T extends TPosition
	?
			| BarLine
			| Note<T>
			| FutureModifier<T>
			| ParallelNotes<T>
			| SequentialNotes<T>
	: unknown;

export type SequentialNotes<T extends TValidate = TPosition> =
	| NoteItem<T>[]
	| (IProperties<T> & { notes: NoteItem<T>[] });

export type ParallelNotes<T extends TValidate = TPosition> = Modified<
	{ voices: SequentialNotes<T>[] },
	IProperties<T>
>;

export type Voice<
	T extends TValidate = TPosition,
	V extends "inline" | "standalone" = "inline",
> = VoiceModifier<T extends TPosition ? T : TPosition> & {
	// Prevents a song loading a voice in a file which loads the notes in another file.
	// Would complicate caching, and who would write it like that anyway.
	notes: SequentialNotes<T> | (V extends "inline" ? FileRef : never);
};
