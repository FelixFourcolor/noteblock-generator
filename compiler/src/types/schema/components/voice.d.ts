import type { BarLine } from "@/types/schema/note";
import type { IGlobal, IProperties, PresetId, TPosition } from "../properties";
import type { Note } from "./note";
import type { FileRef } from "./ref";

export type FutureModifier<T = TPosition> = IProperties<T> | PresetId;

export type TValidate = TPosition | "lazy";

// Required to avoid circular JSON schema references.
type NoteItem<T extends TValidate = TPosition> = T extends TPosition
	? BarLine | Note<T> | FutureModifier<T> | SubNotes<T>
	: unknown;

export type Notes<T extends TValidate = TPosition> = NoteItem<T>[];

export type SubNotes<T extends TValidate = TPosition> =
	| NoteItem<T>[]
	| (IProperties<T> & { notes: NoteItem<T>[] });

export type VoiceModifier<T extends TPosition = TPosition> = IGlobal<
	IProperties<T>
>;

export type Voice<
	T extends TValidate = TPosition,
	V extends "inline" | "standalone" = "inline",
> = VoiceModifier<T extends TPosition ? T : TPosition> & {
	// Prevents a song loading a voice in a file which loads the notes in another file.
	// Would complicate caching, and who would write it like that anyway.
	notes: Notes<T> | (V extends "inline" ? FileRef : never);
};
