import type { Int } from "#schema/utils/@";
import type { Static } from "../meta.ts";

export type Delay = Int<1, 4>;

export type IDelay = {
	/**
	 * How many redstone ticks between consecutive notes (default 1).
	 */
	delay?: Static<Delay>;
};
