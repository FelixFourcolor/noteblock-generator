import type { Duration } from "#schema/duration.ts";
import type { Int, Re, Token } from "#schema/utils/@";
import type { IPositional, Positional } from "../meta.ts";

export type ISustain = {
	/**
	 * How long to sustain the note. Can be "true" (full sustain) or a value for the number of ticks. Negative value means subtract from the note's duration.
	 * Default -1.
	 */
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
