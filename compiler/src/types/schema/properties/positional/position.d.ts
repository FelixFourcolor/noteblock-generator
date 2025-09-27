import type { Variable } from "#types/schema/duration.ts";
import type { Cover, Re, Token } from "#types/utils/@";
import type { Positional } from "../meta.ts";
import type { Division, IDivision } from "./division.ts";
import type { ILevel, Level } from "./level.ts";

export type Position = Position.variable;

export namespace Position {
	export type uniform = uniform.absolute | uniform.relative;
	export namespace uniform {
		export type absolute =
			| Re<Division.uniform.absolute>
			| Level.uniform.absolute
			| Re<Division.uniform.absolute, "\\s*", Level.uniform.absolute>;
		export type relative =
			| Re<Token<Division.uniform>, "?", Level.uniform.relative>
			| Re<Division.uniform.relative, Token<Level.uniform>, "?">;
	}
	export type variable = Variable<uniform | Re<"~">>;
}

export type TPosition = "single" | "double";

export type IPosition<T extends TPosition> = Cover<
	T extends "single"
		? { position: Positional<Level> } | ILevel
		: { position: Positional<Position> } | (ILevel & IDivision),
	"division" | "level" | "position"
>;
