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

export type IDivision = { division?: Positional<Division> };
