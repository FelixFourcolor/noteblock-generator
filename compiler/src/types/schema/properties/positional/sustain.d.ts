import type { Int, Re, Token } from "@/types/helpers";
import type { Duration } from "@/types/schema/duration";
import type { IPositional, Positional } from "../meta";

export type ISustain = {
	sustain?: Positional<Sustain.Value> | IPositional<Sustain>;
};

export type Sustain = {
	min: Sustain.Value;
	max: Sustain.Value;
	value: Sustain.Value;
};

export namespace Sustain {
	export type Value = Value.absolute | Value.relative;
	export namespace Value {
		export type absolute = boolean | Int | Duration.determinate;
		export type relative = Re<"[+-]", Token<absolute, `"`>>;
	}
}
