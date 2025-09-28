import type { Variable } from "#types/schema/duration.ts";
import type { Int, Re, Token } from "#types/utils/@";
import type { Positional } from "../meta.ts";

export type Level = Int<0> | Level.variable;

export namespace Level {
	export type uniform = uniform.absolute | uniform.relative;
	export namespace uniform {
		export type absolute = Int<0> | Re<"\\d+">;
		export type relative = Re<"[+-]", Token<uniform.absolute>>;
	}
	export type variable = Variable<uniform | Re<"~">>;
}

export type ILevel = { level?: Positional<Level> };
