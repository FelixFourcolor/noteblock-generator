import type { Int, Re, Token } from "@/types/helpers";
import type { Variable } from "@/types/schema/duration";
import type { Positional } from "../meta";

export type Level = Int | Level.variable;

export namespace Level {
	export type uniform = Int | Re<Token<"[+-]?">, "\\d+">;
	export type variable = Variable<uniform | Re<"~">>;
}

export type ILevel = {
	level?: Positional<Level>;
};
