import type { Variable } from "#types/schema/duration.ts";
import type { Int, Re, Token } from "#types/utils/@";
import type { Positional } from "../meta.ts";

export type Dynamic = Int<0, 6> | Dynamic.variable;

export namespace Dynamic {
	export type uniform = uniform.absolute | uniform.relative;
	export namespace uniform {
		export type absolute = Int<0, 6> | Re<"[0-6]">;
		export type relative = Re<"[+-]", Token<uniform.absolute>>;
	}
	export type variable = Variable<uniform | Re<"~">>;
}

export type IDynamic = { dynamic?: Positional<Dynamic> };
