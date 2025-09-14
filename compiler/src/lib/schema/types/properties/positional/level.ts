import type { Int, Re, RePartial, Token } from "#lib/schema/types/utils/@";
import type { Positional } from "../meta.ts";
import type { Variable } from "../variable.ts";

export type Level = Level.uniform | Level.variable;
export interface ILevel {
	level: Positional<Level>;
}

export namespace Level {
	export type absolute = uniform.absolute | variable.absolute;
	export type relative = uniform.relative | variable.relative;

	export type uniform = uniform.absolute | uniform.relative;
	export namespace uniform {
		export type absolute = Int<0> | Re<"\\d+">;
		export type relative = Re<"[+-]", Token<uniform.absolute>>;
	}

	export type variable = variable.absolute | variable.relative;
	export namespace variable {
		export type absolute = Variable<uniform.absolute>;
		export type relative = Variable<uniform | Re<"~">> &
			RePartial<uniform.relative | Re<"~">>;
	}
}
