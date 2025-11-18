import type { Variable } from "#schema/duration.ts";
import type { Int, Re, Token } from "#schema/utils/@";
import type { Positional } from "../meta.ts";

export type Level = Int | Level.variable;

export namespace Level {
	export type uniform = Int | Re<Token<"[+-]?">, "\\d+">;
	export type variable = Variable<uniform | Re<"~">>;
}

export type ILevel = {
	level?: Positional<Level>;
};
