import type { Int } from "#schema/utils/@";
import type { Static } from "../meta.ts";

export type Beat = Int<1, 8>;

export type IBeat = {
	/**
	 * When a note has its duration omitted, this beat value is used (default 4).
	 * Duration can also be expressed in terms of beats, e.g., "c:2b" has duration 2 beats.
	 */
	beat?: Static<Beat>;
};
