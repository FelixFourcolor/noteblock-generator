import type { Variable } from "#schema/duration.ts";
import type { Int, Re, Token } from "#schema/utils/@";
import type { Positional } from "../meta.ts";

export type Level = Int | Level.variable;

export namespace Level {
	export type uniform = Int | Re<Token<"[+-]?">, "\\d+">;
	export type variable = Variable<uniform | Re<"~">>;
}

export type ILevel = {
	/**
	 * Where to place the note vertically, higher means closer to the player.
	 * This is one way to control volume, dynamic being the other one. A +1 in level has much less effect than a +1 in dynamic.
	 */
	level?: Positional<Level>;
};
