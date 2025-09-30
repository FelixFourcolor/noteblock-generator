import type { Int, Re, Token } from "#utils/@";
import type { IPositional, Positional } from "../meta.ts";

export type Transpose = {
	value: Transpose.Value;
	auto: Transpose.Auto;
};

export namespace Transpose {
	export type Value = absolute | relative;
	export type Auto = boolean;

	export type absolute = Int;
	export type relative = Re<"[+-]", Token<"\\d+">>;
}

export type ITranspose = {
	transpose?: IPositional<Transpose> | Positional<Transpose.Value>;
};
