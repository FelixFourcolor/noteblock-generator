import { equals, is } from "typia";
import { PresetError } from "@/core/resolver/properties";
import type {
	BarLine,
	FutureModifier,
	Note,
	ParallelNotes,
	SequentialNotes,
} from "@/types/schema";
import type { Context } from "../context";
import type { IMeasure } from "../measure";
import { resolveNote } from "../note";
import type { Tick } from "../tick";
import { zip } from "../utils/generators";
import { resolveBarLine } from "./barline";

export function* resolveNotes(
	notes: SequentialNotes<"lazy">,
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

type BarLineState = { present: boolean };
type NotesState = {
	measure: IMeasure;
	barline: BarLineState;
};

function notesStateComparator(a: NotesState, b: NotesState) {
	return (
		b.measure.bar - a.measure.bar ||
		b.measure.tick - a.measure.tick ||
		(b.barline.present ? 1 : 0) - (a.barline.present ? 1 : 0)
	);
}

function* _resolveNotes(
	notesData: SequentialNotes<"lazy">,
	voiceContext: Context,
	barline = { present: false },
): Generator<Tick, NotesState | undefined> {
	const { notes, modifier } = normalizeNotes(notesData);
	const context = voiceContext.fork(modifier);

	for (const item of notes) {
		if (equals<FutureModifier>(item)) {
			context.transform(item);
			continue;
		}

		if (is<BarLine>(item)) {
			const success = yield* resolveBarLine(item, context);
			if (!success) {
				return;
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

		if (equals<ParallelNotes<"lazy">>(item)) {
			const { voices, modifier } = normalizeVoices(item);
			const parallelContext = context.fork(modifier);
			const results = yield* zip(
				voices.map((voice) =>
					_resolveNotes(voice, parallelContext, { ...barline }),
				),
			);

			const successes = results.filter((res) => res !== undefined);
			if (successes.length !== voices.length) {
				return;
			}
			const furthest = successes.toSorted(notesStateComparator)[0];
			if (furthest) {
				barline.present = furthest.barline.present;
				context.transform(furthest.measure);
			}
			continue;
		}

		if (equals<SequentialNotes<"lazy">>(item)) {
			const result = yield* _resolveNotes(item, context, barline);
			if (!result) {
				return;
			}
			barline.present = result.barline.present;
			context.transform(result.measure);
			continue;
		}

		yield* error(`Invalid entry: ${JSON.stringify(item)}`, context);
		return;
	}

	return { measure: context.measure, barline };
}

function normalizeNotes(value: SequentialNotes<"lazy">) {
	if (Array.isArray(value)) {
		return { notes: value, modifier: {} };
	}
	const { notes, ...modifier } = value;
	return { notes, modifier };
}

function normalizeVoices(value: ParallelNotes<"lazy">) {
	if (Array.isArray(value)) {
		return { voices: value, modifier: {} };
	}
	const { voices, ...modifier } = value;
	return { voices, modifier };
}

function* error(error: string, context: Context) {
	const { voice, measure } = context;
	yield [{ error, voice, measure }];
}
