import type { Re, Repeat, Token } from "#utils/@";

export type Timed<Value> = Re<Value, Duration.optional>;
export type Untimed<T> = T extends Timed<infer V> ? Re<V> : never;

export type Variable<T> = Repeat<Timed<T>, { separator: ";" }>;

export type Duration = Duration.required;

export namespace Duration {
	export type determinate = required.determinate;
	export type indeterminate = required.indeterminate;

	export type required = required.determinate | required.indeterminate;
	export namespace required {
		export type determinate = Re<
			Token<"[+-]">,
			"?",
			DurationPattern,
			Repeating,
			"*"
		>;
		export type indeterminate = Token<"\\.{3}">;
	}

	export type optional = optional.determinate | optional.indeterminate;
	export namespace optional {
		export type determinate = Re<Re<Token<":">, required.determinate>, "?">;
		export type indeterminate = Re<Re<Token<":">, required.indeterminate>, "?">;
	}
}

type DurationPattern = Re<
	"[1-9]\\d*", // positive number
	"b?", // optional "b" for beat
	"\\.?" // optional dotted rhythm
>;
type Repeating = Re<Token<"[+-]" | "\\s">, DurationPattern>;
