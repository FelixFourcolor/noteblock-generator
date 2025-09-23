import { match, P } from "ts-pattern";
import { is } from "typia";
import type {
	Instrument,
	NoteBlock,
	OneOrMany,
	ResolvedType,
} from "#core/resolver/@";
import { parseDuration, resolveTimedValue } from "#core/resolver/duration.js";
import { isMulti, multi } from "#core/resolver/properties/@";
import type { Duration, NoteValue, Pitch, Trill } from "#types/schema/@";
import type { Context } from "../context.js";
import type { TickEvent } from "../types.js";

export function* resolveNoteblocks(args: {
	noteValue: NoteValue;
	trillValue: Trill.Value | undefined;
	context: Context;
}): Generator<OneOrMany<TickEvent> | undefined> {
	const { noteValue, trillValue, context } = args;
	const { beat, time, delay } = context.resolve();
	const { value: pitch, duration } = resolveTimedValue(noteValue, beat);
	const noteDuration = duration ?? time - context.tick + 1;

	if (is<NoteValue.Rest>(noteValue)) {
		return yield* rest({ noteDuration, delay });
	}

	const instrumentResult = resolveInstrument({ pitch, trillValue, context });
	if ("error" in instrumentResult) {
		return yield* error({ ...instrumentResult, noteDuration });
	}

	const { main: mainBlock, trill: trillBlock } = instrumentResult;
	const trill = resolveTrill({ noteDuration, context });
	for (let i = 0; i < noteDuration; ++i) {
		let noteblock = mainBlock;
		if (i >= trill.start && i < trill.end) {
			if (i % 2 === ["alt", "normal"].indexOf(trill.style)) {
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

function resolveInstrument(args: {
	pitch: Pitch;
	trillValue: Trill.Value | undefined;
	context: Context;
}):
	| { main: OneOrMany<NoteBlock>; trill: OneOrMany<NoteBlock> }
	| { error: string } {
	const { pitch, trillValue, context } = args;
	let instrument: ResolvedType<typeof Instrument>;
	try {
		instrument = context.resolve({ pitch, trill: trillValue }).instrument;
	} catch (e) {
		return { error: (e as Error).message };
	}
	return isMulti(instrument)
		? {
				main: multi(instrument.map(({ main }) => main)),
				trill: multi(instrument.map(({ trill }) => trill)),
			}
		: instrument;
}

function* error(args: { noteDuration: number; error: string }) {
	const { error, noteDuration } = args;
	yield { error };
	for (let i = noteDuration - 1; i--; ) {
		yield undefined;
	}
}

function resolveTrill(args: { noteDuration: number; context: Context }) {
	const { noteDuration, context } = args;
	const { beat, trill } = context.resolve();
	return {
		start: resolveDuration(trill.start, { beat, noteDuration }),
		end: resolveDuration(trill.end, { beat, noteDuration }),
		style: trill.style,
	};
}

function resolveDuration(
	value: number | Duration,
	{ beat, noteDuration }: { beat: number; noteDuration: number },
) {
	return match(value)
		.with(P.string, (value) => {
			const parsedValue = parseDuration(value, beat) ?? noteDuration;
			return Math.min(noteDuration, parsedValue);
		})
		.with(P.number.positive(), (value) => Math.min(noteDuration, value))
		.otherwise((value) => Math.max(0, noteDuration + value));
}
