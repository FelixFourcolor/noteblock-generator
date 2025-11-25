import type { Int, Re, Token } from "#types/helpers/@";
import type { IPositional, Positional } from "../meta.ts";

export type Transpose = {
	value: Transpose.Value;
	auto: Transpose.Auto;
};

export namespace Transpose {
	export type Value = Int | Re<Token<"[+-]?">, "\\d+">;
	export type Auto = boolean;
}

export type ITranspose = {
	transpose?: IPositional<Transpose> | Positional<Transpose.Value>;
};
