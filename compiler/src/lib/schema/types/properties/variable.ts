import type { Timed } from "#lib/schema/types/note/@";
import type { Repeat } from "#lib/schema/types/utils/@";

export type Variable<T> =
	| Repeat<Timed<T, "required">, { atLeast: 1; separator: ";" }>
	| Repeat<Timed<T, "optional">, { atLeast: 2; separator: ";" }>;
