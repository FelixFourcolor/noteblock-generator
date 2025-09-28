import type { TickEvent } from "#core/resolver/@";
import type { NoteEvent } from "./types.js";

type ValidateResult<T> = { value: T } | { error: string };

export function validateConsistency<
	E extends TickEvent.Voiced,
	P extends string & keyof E,
>(events: E[], property: P): ValidateResult<E[P]> {
	const propertyByVoice = new Map<string, { value: E[P]; voice: string }>();
	events.forEach((event) => {
		const { voice } = event;
		const value = event[property];
		propertyByVoice.set(JSON.stringify(value), { value, voice });
	});

	if (propertyByVoice.size > 1) {
		const entries = Array.from(propertyByVoice.values());
		const voices = entries.map(({ voice }) => voice);
		const values = entries.map(({ value }) => value);
		return {
			error: `${voices.join(", ")}: Inconsistent ${property}: 
            ${values.map((v) => JSON.stringify(v)).join(", ")}`,
		};
	}

	return { value: events[0]![property] };
}

export function checkOverflow({
	noteGroups,
	onError,
}: {
	noteGroups: Record<string, NoteEvent[]>;
	onError: (_: { groupKey: string; voices: string[]; count: number }) => void;
}) {
	for (const [groupKey, notes] of Object.entries(noteGroups)) {
		const count = notes.length;
		if (count > 6) {
			const voices = Array.from(new Set(notes.map(({ voice }) => voice)));
			onError({ groupKey, voices, count });
		}
	}
}
