import { equals, is } from "typia";
import { validateVoice } from "#core/validator/@";
import type { BarLine, Deferred, FutureModifier, Voice } from "#types/schema/@";
import { Context } from "../context.js";
import { resolveNote } from "../note/note.js";
import type { VoiceContext, VoiceResolution } from "../resolution.js";
import type { Tick } from "../tick.js";
import { resolveBarLine } from "./barline.js";

export async function resolveVoice(
	voice: Deferred<Voice>,
	ctx: VoiceContext,
): Promise<VoiceResolution> {
	const { songModifier, index } = ctx;
	const validated = await validateVoice({ ...ctx, voice });

	if ("error" in validated) {
		return error({ ...validated, index });
	}

	const { type, notes, name, modifier } = validated;

	const context = new Context(name)
		.transform({ level: index })
		.transform(songModifier)
		.fork(modifier);

	// This function is synchronous, but it's wrapped in async
	// so that the API is identical to the threaded version.
	async function* generator(): AsyncGenerator<Tick> {
		let hasBarLine = false;

		for (const item of notes) {
			// must check "equals" instead of "is" because modifier is a subtype of note
			if (equals<FutureModifier>(item)) {
				context.transform(item);
				continue;
			}

			if (is<BarLine>(item)) {
				yield* resolveBarLine(item, context);
				hasBarLine = true;
				continue;
			}

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
					voice: name,
					// measure updates each iteration, cannot factor out
					measure: context.measure,
				}));
				context.transform({ noteDuration: 1 });
			}
		}
	}

	const { time } = context.resolveStatic();
	return { time, type, ticks: generator() };
}

function error({ error, index }: { error: string; index: number }) {
	const type = "single" as const;
	const ticks = (async function* () {
		yield [{ error, voice: `Voice ${index}`, measure: { bar: 1, tick: 1 } }];
	})();
	return { time: NaN, type, ticks };
}
