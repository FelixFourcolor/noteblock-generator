import type { Re } from "#types/helpers/@";

export type Pitch = Pitch.absolute | Pitch.relative | Pitch.implied;
export namespace Pitch {
	export type relative = Re<PitchName, Octave.relative>;
	export type absolute = Re<PitchName, Octave.absolute>;
	export type implied = PitchName;
}

type Letter = "[a-g]";
type Accidental =
	| "b{0,2}" // flat
	| "#{0,2}" // sharp
	| "s{0,2}"; // alias for sharp
type PitchName = Re<Letter, Accidental>;

declare namespace Octave {
	export type absolute = "[1-7]";
	export type relative =
		| "_+" // down from default
		| "\\^+"; // up from default
}
