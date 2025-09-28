import type { tags } from "typia";
import type { AtLeastOneOf } from "#utils/@";

export type Reset = "$reset";
export type Delete = "$delete";

export type Static<T> = T | Reset;

export type Positional<T> =
	| (T | Reset)
	| ((T | Reset | Delete | null)[] & tags.MinItems<1>);
export type IPositional<T> = AtLeastOneOf<{ [K in keyof T]: Positional<T[K]> }>;
