import { parentPort, workerData } from "node:worker_threads";
import { equals, is } from "typia";
import type {
	Barline,
	Chord,
	Deferred,
	FutureModifier,
	Name,
	TPosition,
	Voice,
} from "#core/types/@";
import { validateVoice } from "#core/validator/@";
import { Context, type MutableContext } from "./context.js";
import { resolveChord, resolveNote } from "./note.js";
import type { TEvent } from "./noteblock.js";
import type { PhrasedEvent } from "./phrasing.js";
import type { SongContext } from "./song.js";

if (parentPort) {
	const port = parentPort;
	const args = workerData as Parameters<typeof resolveVoice>;

	resolveVoice(...args).then(async ({ type, ticks }) => {
		port.postMessage(type);

		for await (const tick of ticks) {
			port.postMessage(tick);
		}

		port.postMessage("done");
	});
}

export type Measure = { bar: number; tick: number };

export type SourcedEvent<T extends TEvent = TEvent> = PhrasedEvent<T> & {
	voice: Name;
	measure: Measure;
};

export type Tick = SourcedEvent[];

export interface VoiceResolution {
	type: TPosition;
	ticks: AsyncGenerator<Tick>;
}

export interface VoiceContext extends SongContext {
	index: number;
}

export async function resolveVoice(
	voice: Deferred<Voice>,
	ctx: VoiceContext,
): Promise<VoiceResolution> {
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
			} else if (is<Barline>(item)) {
				yield* resolveBarLine(item, context);
			} else {
				const generator = is<Chord>(item)
					? resolveChord(item, context)
					: resolveNote(item, context);
				for (const tick of generator) {
					if (context.tick === 1) {
						// The barline yields a step to indicate success.
						// If no barline is placed at the start of the bar,
						// we must also yield a step for consistency.
						yield [];
					}
					const { name: voice, measure } = context;
					yield tick.map((event) => ({ ...event, voice, measure }));
					context.transform({ noteDuration: 1 });
				}
			}
	}

	return { type, ticks: generator() };
}

function* resolveBarLine(
	barline: Barline,
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
			yield [{ delay, voice: context.name, measure: context.measure }];
			context.transform({ noteDuration: 1 });
		}
	}
}
