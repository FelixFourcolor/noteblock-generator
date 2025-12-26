import { equals, is } from "typia";
import type {
	BarLine,
	IProperties,
	Note,
	Notes,
	SubNotes,
} from "@/types/schema";
import type { MutableContext } from "../context";
import { resolveNote } from "../note";
import type { Tick } from "../tick";
import { resolveBarLine } from "./barline";

export const resolveNotes: (
	notes: Notes<"lazy">,
	context: MutableContext,
) => Generator<Tick> = _resolveNotes;

function* _resolveNotes(
	notes: Notes<"lazy">,
	context: MutableContext,
	barline = { present: false },
): Generator<Tick, boolean> {
	for (const item of notes) {
		if (equals<IProperties>(item)) {
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

		if (equals<SubNotes<"lazy">>(item)) {
			const { notes, modifier } = normalize(item);
			const subContext = context.fork(modifier);
			const success = yield* _resolveNotes(notes, subContext, barline);
			if (!success) {
				return false;
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
		return false;
	}
	return true;
}

function normalize(subnotes: SubNotes<"lazy">) {
	if (Array.isArray(subnotes)) {
		return { notes: subnotes };
	}
	const { notes, ...modifier } = subnotes;
	return { notes, modifier };
}
