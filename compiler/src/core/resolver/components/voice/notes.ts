import { equals, is } from "typia";
import { PresetError } from "@/core/resolver/properties";
import type { BarLine, FutureModifier, Note, Notes } from "@/types/schema";
import type { Context } from "../context";
import { resolveNote } from "../note";
import type { Tick } from "../tick";
import { resolveBarLine } from "./barline";

export function* resolveNotes(
	notes: Notes<"lazy">,
	context: Context,
): Generator<Tick> {
	try {
		return yield* _resolveNotes(notes, context);
	} catch (e) {
		if (e instanceof PresetError) {
			return yield* error(e.message, context);
		}
		throw e;
	}
}

function* _resolveNotes(
	notesData: Notes<"lazy">,
	voiceContext: Context,
	barline = { present: false },
): Generator<Tick, boolean> {
	const { notes, modifier } = normalize(notesData);
	const context = voiceContext.fork(modifier);

	for (const item of notes) {
		if (equals<FutureModifier>(item)) {
			context.transform(item);
			continue;
		}

		if (is<BarLine>(item)) {
			const success = yield* resolveBarLine(item, context);
			if (!success) {
				return false;
			}
			barline.present = true;
			continue;
		}

		if (equals<Note>(item)) {
			for (const tick of resolveNote(item, context)) {
				// The barline yields a tick to indicate success/failure.
				// If this is the start of a measure without a barline,
				// must also yield an empty tick to synchronize with other voices
				// (that may have a barline at this position)
				if (context.tick === 1 && !barline.present) {
					yield [];
				}
				barline.present = false;

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

		if (equals<Notes<"lazy">>(item)) {
			const success = yield* _resolveNotes(item, context, barline);
			if (!success) {
				return false;
			}
			continue;
		}

		return yield* error(`Invalid entry: ${JSON.stringify(item)}`, context);
	}
	return true;
}

function normalize(Notes: Notes<"lazy">) {
	if (Array.isArray(Notes)) {
		return { notes: Notes, modifier: {} };
	}
	const { notes, ...modifier } = Notes;
	return { notes, modifier };
}

function* error(error: string, context: Context) {
	const { voice, measure } = context;
	yield [{ error, voice, measure }];
	return false;
}
