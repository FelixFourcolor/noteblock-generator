import type { Int } from "#types/helpers/@";
import type { Static } from "../meta.ts";

export type Time = Int<6, 48>;

export type ITime = {
	time?: Static<Time>;
};
