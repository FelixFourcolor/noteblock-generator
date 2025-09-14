import { type } from "arktype";
import { type Pattern, re } from "#lib/new-schema/regex.js";

const pattern = re(
	"[1-9]\\d*", // positive number
	"b?", // optional "b" for beat
	"\\.?", // optional dotted rhythm
);
const repeating = re(re.union("\\s*", re.token("[+-]")), pattern);

const determinate = re(pattern, repeating, "*");
const indeterminate = re("\\.{3}");

export const duration = Object.assign(re.union(determinate, indeterminate), {
	determinate,
	indeterminate,
});

export const Duration = Object.assign(type(duration).brand("Duration"), {
	Determinate: type(determinate).brand("Duration.Determinate"),
	Indeterminate: type(indeterminate).brand("Duration.Indeterminate"),
});

export function timed(
	pattern: Pattern,
	type: "optional" | "required" = "optional",
) {
	if (type === "required") {
		return re(pattern, re.token(":"), duration);
	}
	return re(pattern, re(re.token(":"), duration), "?");
}
