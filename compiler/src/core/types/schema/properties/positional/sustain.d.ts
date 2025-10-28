import type { Duration } from "#schema/duration.ts";
import type { Int, Re, Token } from "#utils/@";
import type { Positional } from "../meta.ts";

export type Sustain = Sustain.absolute | Sustain.relative;

export type ISustain = {
	/**
	 * How long to sustain the note. Can be "true" (full sustain) or a value for the number of ticks. Negative value means subtract from the note's duration.
	 * Default -1.
	 */
	sustain?: Positional<Sustain>;
};

export namespace Sustain {
	export type absolute = boolean | Int | Duration.determinate;
	export type relative = Re<"[+-]", Token<absolute, `"`>>;
}
