import type { TickEvent } from "@/core/resolver";

type ConflictMap<
	E extends TickEvent.Voiced,
	P extends string & keyof E,
> = Record<string, { value: E[P]; voices: Set<string> }>;

const NO_DEFAULT = Symbol("no default");

export function validateConsistency<
	E extends TickEvent.Voiced,
	P extends string & keyof E,
>(
	events: E[],
	property: P,
	defaultValue: E[P] | typeof NO_DEFAULT = NO_DEFAULT,
): { value: E[P]; defaultValue: E[P] } | { error: string } {
	const conflictMap: ConflictMap<E, P> = {};
	events.forEach((event) => {
		const { voice } = event;
		const value = event[property];
		const key = JSON.stringify(value);

		if (conflictMap[key]) {
			conflictMap[key].voices.add(voice);
		} else {
			conflictMap[key] = { value, voices: new Set([voice]) };
		}
	});

	const conflicts = Object.values(conflictMap);
	if (conflicts.length === 0) {
		throw new Error("Events array is empty.");
	}

	if (conflicts.length === 1) {
		const value = events[0]![property];
		return { value, defaultValue: value };
	}

	const values = conflicts.map(({ value }) => value);
	if (
		conflicts.length === 2 &&
		defaultValue !== NO_DEFAULT &&
		values.includes(defaultValue)
	) {
		const otherValue = values.find((v) => v !== defaultValue)!;
		return { value: otherValue, defaultValue };
	}

	const voices = conflicts.map(({ voices }) => voices.values().next().value!);
	return {
		error:
			`${voices.join(", ")}: Inconsistent ${property}s: ` +
			`${values.map((v) => JSON.stringify(v)).join(", ")}`,
	};
}
