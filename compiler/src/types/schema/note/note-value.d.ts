import type { Timed } from "#types/schema/duration.ts";
import type { Pitch } from "./pitch.ts";

export type NoteValue = NoteValue.Rest | NoteValue.Note;

export namespace NoteValue {
	export type Rest = Timed<"R">;
	export type Note = Timed<Pitch>;
}
