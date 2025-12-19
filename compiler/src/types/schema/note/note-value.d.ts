import type { Re, Repeat } from "@/types/helpers";
import type { Timed, Untimed } from "../duration";
import type { Pitch } from "./pitch";

export type NoteValue =
	| NoteValue.Simple
	| NoteValue.Chord
	| NoteValue.Quaver
	| NoteValue.Slur;

export namespace NoteValue {
	export type Rest = Timed<"R">;
	export type Note = Timed<Pitch>;
	export type Simple = Rest | Note;

	export type Chord = Timed<
		Repeat<Pitch, { atLeast: 2; wrapper: ["\\(", "\\)"]; separator: ";" }>
	>;

	export type Quaver = Timed<
		Repeat<
			Re<Untimed<Simple | Chord>>,
			{ atLeast: 1; separator: "'"; strict: true }
		>
	>;

	export type Slur = Repeat<
		Note | Chord | Quaver,
		{ atLeast: 2; separator: "--" }
	>;
}
