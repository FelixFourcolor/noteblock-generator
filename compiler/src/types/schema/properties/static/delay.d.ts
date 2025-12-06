import type { Int } from "@/types/helpers";
import type { Static } from "../meta";

export type Delay = Int<1, 4>;

export type IDelay = {
	delay?: Static<Delay>;
};
