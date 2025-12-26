import type { BarLine } from "@/types/schema/note";
import type { IGlobal, IProperties, TPosition } from "../properties";
import type { Note } from "./note";
import type { FileRef } from "./ref";

export type TValidate = TPosition | "lazy";

// Required to avoid circular JSON schema references.
type NoteItem<T extends TValidate = TPosition> = T extends TPosition
	? BarLine | Note<T> | IProperties<T> | SubNotes<T>
	: unknown;

export type Notes<T extends TValidate = TPosition> = NoteItem<T>[];

export type SubNotes<T extends TValidate = TPosition> =
	| NoteItem<T>[]
	| (IProperties<T> & { notes: NoteItem<T>[] });

export type Voice<
	T extends TValidate = TPosition,
	V extends "inline" | "standalone" = "inline",
> = IGlobal<IProperties<T>> & {
	// Prevents a song loading a voice in a file which loads the notes in another file.
	// Would complicate caching, and who would write it like that anyway.
	notes: Notes<T> | (V extends "inline" ? FileRef : never);
};
