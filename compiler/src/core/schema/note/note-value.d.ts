import type { Timed, Untimed } from "#schema/duration.ts";
import type { Re, Repeat } from "#schema/utils/@";
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
		Repeat<Quaver.Item, { atLeast: 1; separator: "'"; strict: true }>
	>;
	export namespace Quaver {
		export type Item = Re<Untimed<Simple | Chord>>;
	}
}
