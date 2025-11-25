import type { Int } from "#types/helpers/@";
import type { Static } from "../meta.ts";

export type Time = Int<6, 32>;

export type ITime = {
	time?: Static<Time>;
};
