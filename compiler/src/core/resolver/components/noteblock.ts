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
import type { Delay, Duration, NoteValue, Pitch, Trill } from "#core/types/@";
import type { Context } from "./context.js";
import { chain } from "./generator-utils.js";

export type TEvent = keyof variants;
export type BlockEvent<T extends TEvent = TEvent> = variants[T];

interface variants {
	note: { delay: Delay; noteblock: NoteBlock };
	rest: { delay: Delay; noteblock?: undefined };
	error: { error: string };
}

export function* resolveNoteblocks(args: {
	noteValue: NoteValue.Simple;
	trillValue: Trill.Value | undefined;
	context: Context;
}): Generator<OneOrMany<BlockEvent> | undefined> {
	const { noteValue, trillValue, context } = args;
	if (is<NoteValue.Compound>(noteValue)) {
		return yield* compoundNote({ ...args, noteValue });
	}

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

function compoundNote(args: {
	noteValue: NoteValue.Compound;
	trillValue: Trill.Value | undefined;
	context: Context;
}) {
	const { noteValue } = args;
	return chain(
		noteValue
			.trim()
			.slice(1, -1) // remove wrappers
			.split(";")
			.map((value) => resolveNoteblocks({ ...args, noteValue: value })),
	);
}

function* rest(args: { noteDuration: number; delay: number }) {
	const { noteDuration, delay } = args;
	for (let i = 0; i < noteDuration; i++) {
		yield { delay };
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
