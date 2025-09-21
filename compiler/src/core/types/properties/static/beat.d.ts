import type { Int } from "#core/types/utils/@";
import type { Static } from "../meta.ts";

export type Beat = Int<1, 8>;
export interface IBeat {
	beat: Static<Beat>;
}
