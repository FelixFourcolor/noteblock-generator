import type { Int } from "#types/helpers/@";
import type { Static } from "../meta.ts";

export type Beat = Int<1, 8>;

export type IBeat = {
	beat?: Static<Beat>;
};
