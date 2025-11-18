import type { Int, Re, Token } from "#schema/utils/@";
import type { IPositional, Positional } from "../meta.ts";

export type Transpose = {
	/** Number of semitones */
	value: Transpose.Value;
	/** Whether to automatically transpose up/down an octave if a note doesn't fit the instrument */
	auto: Transpose.Auto;
};

export namespace Transpose {
	export type Value = Int | Re<Token<"[+-]?">, "\\d+">;
	export type Auto = boolean;
}

export type ITranspose = {
	transpose?: IPositional<Transpose> | Positional<Transpose.Value>;
};
