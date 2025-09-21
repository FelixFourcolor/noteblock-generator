import type { Repeat } from "#core/types/utils/@";
import type { Timed } from "./duration.ts";
import type { Pitch } from "./pitch.ts";

export type NoteValue =
	| NoteValue.Simple
	| NoteValue.Continuous
	| NoteValue.Sequential
	| NoteValue.Parallel;

export namespace NoteValue {
	export type Rest = Timed<"R">;

	export type Single = Single.timed;
	export namespace Single {
		export type untimed = Pitch;
		export type timed = Timed<Pitch>;
	}

	export type Compound = Repeat<Single, compound>;

	export type Simple = Rest | Single | Compound;

	export type Continuous = Repeat<Simple, continuous>;

	export type Parallel = Parallel.variable | Parallel.uniform;
	export namespace Parallel {
		export type variable = Repeat<Single.timed, parallel>;
		export type uniform = Timed<Repeat<Single.untimed, parallel>>;
	}

	export type Sequential = Repeat<
		Rest | Single | Compound | Continuous | Parallel,
		sequential
	>;
}

type sequential = { separator: ","; atLeast: 2 };
type continuous = { separator: ";"; atLeast: 2 };
type compound = { separator: ";"; atLeast: 2; wrapper: ["<", ">"] };
type parallel = { separator: ";"; atLeast: 2; wrapper: ["\\(", "\\)"] };
