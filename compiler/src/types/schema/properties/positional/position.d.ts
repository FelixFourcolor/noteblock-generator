import type { Re, Token } from "@/types/helpers";
import type { Variable } from "@/types/schema/duration";
import type { Positional } from "../meta";
import type { Division, IDivision } from "./division";
import type { ILevel, Level } from "./level";

export type Position = (Level & number) | Position.variable;

export namespace Position {
	export type uniform =
		| (Level & number)
		| Re<Token<Division.uniform>, "?", Level.uniform>
		| Re<Division.uniform, Token<Level.uniform>, "?">;
	export type variable = Variable<uniform | Re<"~">>;
}

export type TPosition = "single" | "double";

export type IPosition<T> = T extends "single"
	? { position?: Positional<Level> } | ILevel
	: { position?: Positional<Position> } | (ILevel & IDivision);
