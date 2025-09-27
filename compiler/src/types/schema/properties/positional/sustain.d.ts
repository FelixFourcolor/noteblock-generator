import type { Duration } from "#types/schema/duration.ts";
import type { Int, Re, Token } from "#types/utils/@";
import type { Positional } from "../meta.ts";

export type Sustain = Sustain.absolute | Sustain.relative;
export interface ISustain {
	sustain: Positional<Sustain>;
}

export namespace Sustain {
	export type absolute = boolean | Int | Duration.determinate;
	export type relative = Re<"[+-]", Token<absolute, `"`>>;
}
