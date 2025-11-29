import { equals, is } from "typia";
import type { BarLine, IProperties, Note, Notes } from "#schema/@";
import { resolveNote } from "../note/note.js";
import type { Tick } from "../tick.js";
import type { MutableContext } from "../utils/context.js";
import { resolveBarLine } from "./barline.js";

export function* resolveNotes(
	notes: Notes<"lazy">,
	context: MutableContext,
): Generator<Tick> {
	let hasBarLine = false;

	for (const item of notes) {
		// must check "equals" instead of "is"
		// because a Note is also an IProperties
		if (equals<IProperties>(item)) {
			context.transform(item);
			continue;
		}

		if (is<BarLine>(item)) {
			yield* resolveBarLine(item, context);
			hasBarLine = true;
			continue;
		}

		if (equals<Note>(item)) {
			for (const tick of resolveNote(item, context)) {
				// The barline yields a tick to indicate success/failure.
				// If no barline is placed at the start of the bar,
				// we must also yield a tick for synchronization.
				if (context.tick === 1 && !hasBarLine) {
					yield [];
				}
				hasBarLine = false;

				yield tick.map((event) => ({
					...event,
					voice: context.voice,
					// measure updates each iteration, cannot factor out
					measure: context.measure,
				}));
				context.transform({ noteDuration: 1 });
			}
			continue;
		}

		yield [
			{
				error: "Data does not match schema.",
				voice: context.voice,
				measure: context.measure,
			},
		];
		return;
	}
}
