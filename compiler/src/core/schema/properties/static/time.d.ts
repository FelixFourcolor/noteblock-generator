import type { Int } from "#schema/utils/@";
import type { Static } from "../meta.ts";

export type Time = Int<6, 32>;

export type ITime = {
	/**
	 * @title Time
	 *
	 * How many ticks per bar (default 16). Useful for compile-time bar checking, and also influences how wide the structure is.
	 */
	time?: Static<Time>;
};
