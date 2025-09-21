import type { Int } from "#core/types/utils/@";
import type { Static } from "../meta.ts";

export type Delay = Int<1, 4>;
export interface IDelay {
	delay: Static<Delay>;
}
