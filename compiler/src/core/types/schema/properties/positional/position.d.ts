import type { Variable } from "#schema/duration.ts";
import type { Re, Token } from "#utils/@";
import type { Positional } from "../meta.ts";
import type { Division, IDivision } from "./division.ts";
import type { ILevel, Level } from "./level.ts";

export type Position = (Level & number) | Position.variable;

export namespace Position {
	export type uniform =
		| (Level & number)
		| Re<Token<Division.uniform>, "?", Level.uniform>
		| Re<Division.uniform, Token<Level.uniform>, "?">;
	export type variable = Variable<uniform | Re<"~">>;
}

export type TPosition = "single" | "double";

export type IPosition<T extends TPosition> = T extends "single"
	? { position?: Positional<Level> } | ILevel
	: { position?: Positional<Position> } | (ILevel & IDivision);
