import { times } from "lodash";
import { match, P } from "ts-pattern";
import {
	Dynamic,
	isMulti,
	multiMap,
	type OneOrMany,
	Position,
	Sustain,
} from "@/core/resolver/properties";
import type { TickEvent } from "../tick";
import type { Context } from "../utils/context";

export function* applyPhrasing({
	events,
	context,
}: {
	events: Generator<OneOrMany<TickEvent> | undefined>;
	context: Context;
}): Generator<TickEvent.Phrased[]> {
	const eventsArray = Array.from(events);
	const noteDuration = eventsArray.length;
	const { sustain, dynamic, position } = context.resolvePhrasing(noteDuration);

	function attachProps(event: OneOrMany<TickEvent>) {
		return multiMap(
			({
				noteDuration,
				sustain = Sustain.default({ noteDuration }),
				dynamic = Dynamic.default({ noteDuration, sustain }),
				position = Position.default({ noteDuration, sustain }),
				event,
			}) => ({ ...event, position, dynamic }),
			{ event, noteDuration, sustain, dynamic, position },
		);
	}

	for (const [index, event] of eventsArray.entries()) {
		if (event) {
			yield applyProps(index, attachProps(event));
		} else {
			yield [];
		}
	}
}

type Phrasing = {
	position: { level: number; division: "L" | "R" | "LR" }[];
	dynamic: number[];
};

type EventPhrasing = { [K in keyof Phrasing]: Phrasing[K][number] };

function applyProps(
	index: number,
	props: OneOrMany<TickEvent & Phrasing>,
): TickEvent.Phrased[] {
	return match(props)
		.with(P.when(isMulti), (multiProps) =>
			multiProps.flatMap((prop) => applyProps(index, prop)),
		)
		.with({ noteblock: P.nonNullable }, ({ position, dynamic, ...note }) =>
			createPhrasedEvents({
				...note,
				position: position[index]!,
				dynamic: dynamic[index]!,
			}),
		)
		.with({ error: P._ }, (error) => [error])
		.with({ delay: P.select() }, (delay) => rest(delay))
		.otherwise(() => []);
}

function createPhrasedEvents({
	dynamic,
	position: { level, division },
	...note
}: TickEvent<"note"> & EventPhrasing): TickEvent.Phrased[] {
	if (dynamic === 0) {
		return rest(note.delay);
	}
	if (division === "LR") {
		return times(dynamic).flatMap(() => [
			{ ...note, level, division: "L" },
			{ ...note, level, division: "R" },
		]);
	}
	return times(dynamic, () => ({ ...note, level, division }));
}

function rest(delay: number): TickEvent.Phrased[] {
	return [{ delay, noteblock: undefined }];
}
