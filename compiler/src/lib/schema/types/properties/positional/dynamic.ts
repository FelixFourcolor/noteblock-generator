import type { Int, Re, RePartial, Token } from "#lib/schema/types/utils/@";
import type { Positional } from "../meta.ts";
import type { Variable } from "../variable.ts";

export type Dynamic = Dynamic.uniform | Dynamic.variable;
export interface IDynamic {
	dynamic: Positional<Dynamic>;
}

export namespace Dynamic {
	export type absolute = uniform.absolute | variable.absolute;
	export type relative = uniform.relative | variable.relative;

	export type uniform = uniform.absolute | uniform.relative;
	export namespace uniform {
		export type absolute = Int<0, 6> | Re<"[0-6]">;
		export type relative = Re<"[+-]", Token<uniform.absolute>>;
	}

	export type variable = variable.absolute | variable.relative;
	export namespace variable {
		export type absolute = Variable<uniform.absolute>;
		export type relative = Variable<uniform | Re<"~">> &
			RePartial<uniform.relative | Re<"~">>;
	}
}
