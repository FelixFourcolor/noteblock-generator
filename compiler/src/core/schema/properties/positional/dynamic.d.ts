import type { Variable } from "#schema/duration.ts";
import type { Int, Re, Token } from "#schema/utils/@";
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

export type IDynamic = {
	/**
	 * How many note blocks used to produce each note (default 1). Each redstone dust can power upto 6 note blocks.
	 * This is one way to control volume, level being the other one. A +1 in dynamic has much more effect than a +1 in level.
	 */
	dynamic?: Positional<Dynamic>;
};
