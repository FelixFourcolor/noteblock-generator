import type { Timed } from "#schema/duration.ts";
import type { Re, Repeat, WithDoc } from "#utils/@";
import type { Pitch } from "./pitch.ts";

export type NoteValue = NoteValue.Simple | NoteValue.Chord | NoteValue.Quaver;

export namespace NoteValue {
	export type Rest = WithDoc<Timed<"R">, { title: "Rest" }>;
	export type Note = WithDoc<
		Timed<Pitch>,
		{
			title: "Note";
			description: "Syntax: [pitch]:[duration]. Duration is in number of redstone ticks.";
		}
	>;
	export type Simple = Rest | Note;

	export type Chord = WithDoc<
		Timed<
			Repeat<Pitch, { atLeast: 2; wrapper: ["\\(", "\\)"]; separator: ";" }>
		>,
		{
			title: "Chord";
			description: "Notes played concurrently.";
		}
	>;

	export type Quaver = WithDoc<
		Timed<Repeat<Quaver.Item, { atLeast: 1; separator: "'"; strict: true }>>,
		{
			title: "Quaver";
			description: "These notes are played at half usual length.";
		}
	>;
	export namespace Quaver {
		export type Item = Re<
			| Re<"R">
			| Pitch
			| Repeat<Pitch, { atLeast: 2; wrapper: ["\\(", "\\)"]; separator: ";" }>
		>;
	}
}
