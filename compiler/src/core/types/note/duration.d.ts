import type { Re, Token } from "#core/types/utils/@"; // Removed KeyOf

export type Timed<
	Value,
	Type extends "optional" | "required" = "optional",
> = Type extends "optional"
	? Re<Value, Duration.optional>
	: Re<Value, Token<":">, Duration.required>;

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
	[
		"[1-9]\\d*", // positive number
		"b?", // optional "b" for beat
		"\\.?", // optional dotted rhythm
	]
>;
type Repeating = Re<Token<"[+-]" | "\\s">, DurationPattern>;
