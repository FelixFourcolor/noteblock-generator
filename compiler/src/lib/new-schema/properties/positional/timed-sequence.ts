import { timed } from "#lib/new-schema/note/@";
import { type Pattern, re } from "#lib/new-schema/regex.js";

export function timedSequence(pattern: Pattern) {
	const requiredTime = re.peat(timed(pattern, "required"), {
		atLeast: 1,
		separator: ";",
	});
	const optionalTime = re.peat(timed(pattern, "optional"), {
		atLeast: 2,
		separator: ";",
	});
	return re.union(requiredTime, optionalTime);
}
