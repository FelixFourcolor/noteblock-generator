import type { tags } from "typia";

export type Reset = "$reset";
export type Delete = "$delete";

export type Static<T> = T | Reset;

export type Positional<T> =
	| (T | Reset)
	| ((T | Reset | Delete | null)[] & tags.MinItems<1>);
export type IPositional<T> = Partial<{ [K in keyof T]: Positional<T[K]> }>;

type Global<T> = T extends (infer U)[]
	? Exclude<U, Reset | Delete>[] & tags.MinItems<1>
	: T extends IPositional<infer U>
		? IPositional<U> extends T
			? { [K in keyof U]?: U[K] | (U[K] | null)[] }
			: Exclude<T, Reset>
		: never;
export type IGlobal<T> = { [K in keyof T]: Global<T[K]> };
