import type { Positional } from "../meta.ts";
import type { Variable } from "../variable.ts";

export type Division = Division.uniform | Division.variable;

export namespace Division {
	export type uniform = uniform.absolute | uniform.relative;
	export namespace uniform {
		export type absolute = "L" | "R" | "LR";
		export type relative = "SW";
	}
	export type variable = Variable<uniform | "~">;
}

export interface IDivision {
	division: Positional<Division>;
}
