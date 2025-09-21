import type { Re, Token } from "#core/types/utils/@";
import type { Positional } from "../meta.ts";
import type { Variable } from "../variable.ts";
import type { Division } from "./division.ts";
import type { Level } from "./level.ts";

export type Position = Position.uniform | Position.variable;
export interface IPosition<T extends TPosition = "double"> {
	position: variants[TPosition extends T ? "double" : T];
}

export type TPosition = "single" | "double";
interface variants {
	single: Positional<Level>;
	double: Positional<Position>;
}

export namespace Position {
	export type absolute = uniform.absolute | variable.absolute;
	export type relative = uniform.relative | variable.relative;

	export type uniform = uniform.absolute | uniform.relative;
	export namespace uniform {
		export type absolute =
			| Re<Division.uniform.absolute>
			| Level.uniform.absolute
			| Re<Division.uniform.absolute, "\\s*", Level.uniform.absolute>;
		export type relative =
			| Re<Token<Division.uniform>, "?", Level.uniform.relative>
			| Re<Division.uniform.relative, Token<Level.uniform>, "?">;
	}

	export type variable = variable.absolute | variable.relative;
	export namespace variable {
		export type absolute = Variable<uniform.absolute>;
		export type relative = Variable<uniform | Re<"~">> &
			Re<uniform.relative | Re<"~">>;
	}
}
