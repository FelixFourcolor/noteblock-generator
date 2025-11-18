import type { Duration } from "#schema/duration.ts";
import type { Int, Re, Token } from "#schema/utils/@";
import type { IPositional, Positional } from "../meta.ts";

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
