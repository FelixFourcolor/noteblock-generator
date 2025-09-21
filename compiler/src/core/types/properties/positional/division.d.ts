import type { Re } from "#core/types/utils/@";
import type { Positional } from "../meta.ts";
import type { Variable } from "../variable.ts";

export type Division = Division.uniform | Division.variable;
export interface IDivision {
	division: Positional<Division>;
}

export namespace Division {
	export type absolute = uniform.absolute | variable.absolute;
	export type relative = uniform.relative | variable.relative;

	export type uniform = uniform.absolute | uniform.relative;
	export namespace uniform {
		export type absolute = "L" | "R" | "LR";
		export type relative = "SW";
	}

	export type variable = variable.absolute | variable.relative;
	export namespace variable {
		export type absolute = Variable<uniform.absolute>;
		export type relative = Variable<uniform | "~"> & Re<uniform.relative | "~">;
	}
}
