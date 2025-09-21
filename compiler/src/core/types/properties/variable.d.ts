import type { Timed } from "#core/types/note/@";
import type { Repeat } from "#core/types/utils/@";

export type Variable<T> =
	| Repeat<Timed<T, "required">, { atLeast: 1; separator: ";" }>
	| Repeat<Timed<T, "optional">, { atLeast: 2; separator: ";" }>;
