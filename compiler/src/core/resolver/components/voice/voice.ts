import { equals, is } from "typia";
import { validateVoice } from "#core/validator/@";
import type {
	BarLine,
	Deferred,
	FutureModifier,
	Note,
	Voice,
} from "#types/schema/@";
import { Context, type MutableContext } from "../context.js";
import { resolveNote } from "../note/note.js";
import type { Resolution, Tick, VoiceContext } from "../types.js";

export async function resolveVoice(
	voice: Deferred<Voice>,
	ctx: VoiceContext,
): Promise<Resolution> {
	const { songModifier, index } = ctx;
	const validated = await validateVoice({ ...ctx, voice });
	if ("error" in validated) {
		return {
			type: "single",
			ticks: (async function* () {
				yield [
					{
						error: validated.error,
						voice: `Voice ${index + 1}`,
						measure: { bar: 1, tick: 1 },
					},
				];
			})(),
		};
	}
	const { type, notes, name: voiceName, modifier: voiceModifier } = validated;

	const context = new Context(voiceName)
		.transform({ level: index })
		.transform(songModifier)
		.fork(voiceModifier);

	// This function is synchronous, but it's wrapped in async
	// so that the API is identical to the threaded version.
	async function* generator(): AsyncGenerator<Tick> {
		for (const item of notes)
			if (equals<FutureModifier>(item)) {
				context.transform(item);
			} else if (is<BarLine>(item)) {
				yield* resolveBarLine(item, context);
			} else {
				yield* resolveNoteWithVoice(item, context);
			}
	}

	return { type, ticks: generator() };
}

function* resolveNoteWithVoice(
	note: Note,
	context: MutableContext,
): Generator<Tick> {
	for (const tick of resolveNote(note, context)) {
		if (context.tick === 1) {
			// The barline yields a tick to indicate success/failure.
			// If no barline is placed at the start of the bar,
			// we must also yield a tick for synchronization.
			yield [];
		}
		const { name, measure } = context;
		yield tick.map((event) => ({ ...event, voice: name, measure }));
		context.transform({ noteDuration: 1 });
	}
}

function* resolveBarLine(
	barline: BarLine,
	context: MutableContext,
): Generator<Tick> {
	const numberMatch = barline.match(/\d+/);
	const barNumber = numberMatch ? Number.parseInt(numberMatch[0]) : undefined;
	const restEntireBar = barline.split("|").length > 2;

	const { bar, tick } = context;
	const bypassError = barline.includes("!");
	if (
		!bypassError &&
		((bar !== barNumber && barNumber !== undefined) || tick !== 1)
	) {
		yield [
			{
				error: "Incorrect barline placement",
				voice: context.name,
				measure: context.measure,
			},
		];
	} else {
		yield [];
	}

	context.transform({
		measure: {
			bar: barNumber || bar + 1,
			tick: 1,
		},
	});

	if (restEntireBar) {
		const { delay, time } = context.resolve();
		for (let i = time; i--; ) {
			yield [
				{
					delay,
					noteblock: undefined,
					voice: context.name,
					measure: context.measure,
				},
			];
			context.transform({ noteDuration: 1 });
		}
	}
}
