import type { Timed } from "#schema/duration.ts";
import type { Repeat } from "#utils/@";
import type { Pitch } from "./pitch.ts";

export type NoteValue = NoteValue.Simple | NoteValue.Chord | NoteValue.Quaver;

export namespace NoteValue {
	export type Rest = Timed<"R">;
	export type Note = Timed<Pitch>;
	export type Simple = Rest | Note;

	export type Chord = Timed<
		Repeat<Pitch, { atLeast: 2; wrapper: ["\\(", "\\)"]; separator: ";" }>
	>;
	export type Quaver = Timed<
		Repeat<Rest | Pitch, { atLeast: 2; separator: ";" }>
	>;
}
