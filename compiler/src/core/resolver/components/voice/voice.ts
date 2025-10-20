import { equals, is } from "typia";
import { validateVoice } from "#core/validator/@";
import type { BarLine, Deferred, IProperties, Note, Voice } from "#schema/@";
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
		return {
			time: NaN,
			type: "single",
			ticks: (function* () {
				yield [
					{
						error: validated.error,
						voice: `Voice ${index}`,
						measure: { bar: 1, tick: 1 },
					},
				];
			})(),
		};
	}

	const { type, notes, name, modifier } = validated;

	const level = typeof index === "number" ? index : index[0];
	const context = new Context(name)
		.transform({ level })
		.transform(songModifier)
		.fork(modifier);

	function* generator(): Generator<Tick> {
		let hasBarLine = false;

		for (const item of notes) {
			// must check "equals" instead of "is"
			// because IProperties is a subtype of Note
			if (equals<IProperties>(item)) {
				context.transform(item);
				continue;
			}

			if (is<BarLine>(item)) {
				yield* resolveBarLine(item, context);
				hasBarLine = true;
				continue;
			}

			if (is<Note>(item)) {
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
				continue;
			}

			yield [
				{
					error: "Data does not match schema.",
					voice: name,
					measure: context.measure,
				},
			];
			return;
		}
	}

	const { time } = context.resolveStatic();
	return { time, type, ticks: generator() };
}
