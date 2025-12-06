import { UserError } from "@/cli/error";
import type { IMeasure, NoteEvent, TickEvent } from "@/core/resolver";

export class ErrorTracker {
	private readonly errors = new Map<string, Set<string>>();

	registerError = (error: string | Error, measure: IMeasure) => {
		const key = JSON.stringify(measure);
		const message = typeof error === "string" ? error : error.message;

		if (this.errors.has(key)) {
			this.errors.get(key)!.add(message);
		} else {
			this.errors.set(key, new Set([message]));
		}
	};

	validate() {
		if (this.errors.size) {
			return new UserError(this.formatErrorMessage());
		}
	}

	private formatErrorMessage() {
		const lines: string[] = [];

		this.errors.forEach((errorSet, key) => {
			const { bar, tick } = JSON.parse(key) as IMeasure;
			lines.push(`ERROR @(${bar}, ${tick}):`);

			errorSet.forEach((error) => {
				lines.push(`  - ${error}`);
			});

			lines.push("");
		});

		return lines.slice(0, -1).join("\n");
	}
}

export function validateConsistency<
	E extends TickEvent.Voiced,
	P extends string & keyof E,
>(events: E[], property: P): { value: E[P] } | { error: string } {
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
			error:
				`${voices.join(", ")}: Inconsistent ${property}s: ` +
				`${values.map((v) => JSON.stringify(v)).join(", ")}`,
		};
	}

	return { value: events[0]![property] };
}

export function validateClusterSize(
	noteGroups: Record<string, NoteEvent[]>,
	onError: (e: [string, { voices: string[]; size: number }]) => void,
) {
	for (const [groupKey, notes] of Object.entries(noteGroups)) {
		const size = notes.length;
		if (size > 6) {
			const voices = Array.from(new Set(notes.map(({ voice }) => voice)));
			onError([groupKey, { voices, size }]);
		}
	}
}
