import { match, P } from "ts-pattern";
import { is } from "typia";
import { UserError } from "#cli/error.js";
import type { OneOrMany } from "#core/resolver/@";
import { resolveTimedValue } from "#core/resolver/duration.js";
import { isMulti, multi } from "#core/resolver/properties/@";
import type { NoteValue, Trill } from "#types/schema/@";
import type { Context } from "../context.js";
import type { TickEvent } from "../types.js";

export function* resolveNoteblocks({
	noteValue,
	trillValue,
	context,
}: {
	noteValue: NoteValue;
	trillValue: Trill.Value | undefined;
	context: Context;
}): Generator<OneOrMany<TickEvent> | undefined> {
	const { beat, time, delay } = context.resolveStatic();
	const { value: pitch, duration } = resolveTimedValue(noteValue, beat);
	const noteDuration = duration ?? time - context.tick + 1;

	if (is<NoteValue.Rest>(noteValue)) {
		return yield* rest({ noteDuration, delay });
	}

	let instrument: ReturnType<Context["resolveInstrument"]>;
	try {
		instrument = context.resolveInstrument({ pitch, trillValue });
	} catch (e) {
		if (e instanceof UserError) {
			return yield* error({ error: e, noteDuration });
		}
		throw e;
	}

	const { mainBlock, trillBlock } = instrument;
	const { trillStart, trillEnd, trillStyle } = context.resolveTrill({
		noteDuration,
	});

	for (let i = 0; i < noteDuration; ++i) {
		let noteblock = mainBlock;
		if (i >= trillStart && i < trillEnd) {
			if (i % 2 === ["alt", "normal"].indexOf(trillStyle)) {
				noteblock = trillBlock;
			}
		}
		yield match(noteblock)
			.with(P.when(isMulti), (blocks) =>
				multi(blocks.map((noteblock) => ({ noteblock, delay }))),
			)
			.otherwise((noteblock) => ({ noteblock, delay }));
	}
}

function* rest(args: { noteDuration: number; delay: number }) {
	const { noteDuration, delay } = args;
	for (let i = 0; i < noteDuration; i++) {
		yield { delay, noteblock: undefined };
	}
}

function* error(args: { error: Error; noteDuration: number }) {
	const { error, noteDuration } = args;
	yield { error: error.message };
	for (let i = noteDuration - 1; i--; ) {
		yield undefined;
	}
}
