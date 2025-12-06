import type { Variable } from "@/types/schema/duration";
import type { Positional } from "../meta";

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
	division?: Positional<Division>;
};
