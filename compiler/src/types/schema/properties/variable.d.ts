import type { Timed } from "#types/schema/note/@";
import type { Repeat } from "#types/utils/@";

export type Variable<T> =
	| Repeat<Timed<T, "required">, { atLeast: 1; separator: ";" }>
	| Repeat<Timed<T, "optional">, { atLeast: 2; separator: ";" }>;
