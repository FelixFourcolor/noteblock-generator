import { match, P } from "ts-pattern";
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

function compareMeasure(a: IMeasure, b: IMeasure) {
	return b.bar - a.bar || b.tick - a.tick;
}

function* _resolveNotes(
	notesData: SequentialNotes<"lazy">,
	voiceContext: Context,
): Generator<Tick, IMeasure | undefined> {
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
			continue;
		}

		if (equals<Note>(item)) {
			for (const tick of resolveNote(item, context)) {
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
				voices.map((notes) => _resolveNotes(notes, parallelContext)),
			);

			const successes = results.filter((res) => res !== undefined);
			if (successes.length !== voices.length) {
				return;
			}
			const furthest = successes.toSorted(compareMeasure)[0];
			if (furthest) {
				context.transform(furthest);
			}
			continue;
		}

		if (equals<SequentialNotes<"lazy">>(item)) {
			const endMeasure = yield* _resolveNotes(item, context);
			if (!endMeasure) {
				return;
			}
			context.transform(endMeasure);
			continue;
		}

		yield* error(`Invalid entry: ${JSON.stringify(item)}`, context);
		return;
	}

	return context.measure;
}

function normalizeNotes(value: SequentialNotes<"lazy">) {
	if (Array.isArray(value)) {
		return { notes: value, modifier: {} };
	}
	const { notes, ...modifier } = value;
	return { notes, modifier };
}

function normalizeVoices(value: ParallelNotes<"lazy">) {
	const { voices, modifier } = match(value)
		.with(P.array(), (voices) => ({ voices, modifier: {} }))
		.otherwise(({ voices, ...modifier }) => ({ voices, modifier }));
	const normalizedVoices = voices.map(
		(item): SequentialNotes<"lazy"> => (is<Note>(item) ? [item] : item),
	);
	return { voices: normalizedVoices, modifier };
}

function* error(error: string, context: Context) {
	const { voice, measure } = context;
	yield [{ error, voice, measure }];
}
