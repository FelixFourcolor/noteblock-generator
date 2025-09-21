import type { Int } from "#core/types/utils/@";
import type { Static } from "../meta.ts";

export type Time = Int<6, 32>;
export interface ITime {
	time: Static<Time>;
}
