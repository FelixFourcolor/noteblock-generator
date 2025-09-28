import type { Int } from "#types/utils/@";
import type { Static } from "../meta.ts";

export type Delay = Int<1, 4>;

export type IDelay = { delay?: Static<Delay> };
