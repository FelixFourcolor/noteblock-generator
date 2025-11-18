import type { Variable } from "#schema/duration.ts";
import type { Positional } from "../meta.ts";

export type Division = Division.variable;

export namespace Division {
	export type uniform = uniform.absolute | uniform.relative;
	export namespace uniform {
		export type absolute = "L" | "R" | "LR";
		export type relative = "SW";
	}
	export type variable = Variable<uniform | "~">;
}

export type IDivision = {
	/**
	 * Where to place the note horizontally relative to the player (left, right, or both sides).
	 */
	division?: Positional<Division>;
};
