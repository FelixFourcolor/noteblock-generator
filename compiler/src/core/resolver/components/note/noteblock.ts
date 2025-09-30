import { match, P } from "ts-pattern";
import { is } from "typia";
import { UserError } from "#cli/error.js";
import type { Instrument, OneOrMany, ResolveType } from "#core/resolver/@";
import { resolveTimedValue } from "#core/resolver/duration.js";
import { multiMap, Trill } from "#core/resolver/properties/@";
import type { NoteValue, Trill as T_Trill } from "#schema/@";
import type { Context } from "../context.js";
import type { TickEvent } from "../tick.js";

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

	const trill = context.resolveTrill(noteDuration);

	for (let i = 0; i < noteDuration; ++i) {
		yield multiMap(getNoteBlock, {
			tick: i,
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
	tick: number;
	noteDuration: number;
	delay: number;
	instrument: ResolveType<typeof Instrument>;
	trill: ResolveType<typeof Trill>;
}) {
	const {
		tick,
		delay,
		noteDuration,
		instrument,
		trill = Trill.Default({ noteDuration }),
	} = args;

	if (!instrument) {
		return { delay, noteblock: undefined };
	}

	// normal = start trill on the main note
	// alt = start trill on the trill note
	const styles = ["normal", "alt"] as const;
	const trillIndex = styles.indexOf(trill.style);

	const noteblock = match(tick)
		.with(P.number.gte(trill.start + trill.length), () => instrument[0])
		.with(P.number.lte(trill.start), () => instrument[trillIndex])
		.otherwise(() => instrument[(tick - trill.start + trillIndex) % 2]);

	return { delay, noteblock };
}
