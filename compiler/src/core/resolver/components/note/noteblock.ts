import { is } from "typia";
import { UserError } from "#cli/error.js";
import type { OneOfMulti, OneOrMany } from "#core/resolver/@";
import { resolveTimedValue } from "#core/resolver/duration.js";
import { multiMap, Trill } from "#core/resolver/properties/@";
import type { NoteValue, Trill as T_Trill } from "#types/schema/@";
import type { Context } from "../context.js";
import type { TickEvent } from "../types.js";

export function* resolveNoteblocks({
	noteValue,
	trillValue,
	context,
}: {
	noteValue: NoteValue;
	trillValue: T_Trill.Value | undefined;
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

	const trill = context.resolveTrill({ noteDuration });

	for (let index = 0; index < noteDuration; ++index) {
		yield multiMap(getNoteBlock, {
			index,
			delay,
			noteDuration,
			instrument,
			trill,
		});
	}
}

function* rest(args: { noteDuration: number; delay: number }) {
	for (let i = 0; i < args.noteDuration; i++) {
		yield { delay: args.delay, noteblock: undefined };
	}
}

function* error(args: { error: Error; noteDuration: number }) {
	yield { error: args.error.message };
	for (let i = args.noteDuration - 1; i--; ) {
		yield undefined;
	}
}

function getNoteBlock(args: {
	index: number;
	delay: number;
	noteDuration: number;
	instrument: OneOfMulti<ReturnType<Context["resolveInstrument"]>>;
	trill: OneOfMulti<ReturnType<Context["resolveTrill"]>>;
}) {
	const {
		index,
		delay,
		noteDuration,
		instrument,
		trill = Trill.Default({ noteDuration }),
	} = args;

	if (!instrument) {
		return { delay, noteblock: undefined };
	}

	const { mainBlock, trillBlock } = instrument;

	let noteblock = mainBlock;
	if (trill.enabled) {
		if (index >= trill.start && index < trill.end) {
			if (index % 2 === ["alt", "normal"].indexOf(trill.style)) {
				noteblock = trillBlock;
			}
		}
	}

	return { delay, noteblock };
}
