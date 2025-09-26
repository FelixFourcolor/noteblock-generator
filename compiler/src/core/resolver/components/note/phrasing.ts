import { times } from "lodash";
import { match, P } from "ts-pattern";
import type { OneOrMany } from "#core/resolver/properties/@";
import {
	Dynamic,
	isMulti,
	multiMap,
	Position,
	Sustain,
} from "#core/resolver/properties/@";
import type { Context } from "../context.js";
import type { TickEvent } from "../types.js";

export function* applyPhrasing({
	events,
	context,
}: {
	events: Generator<OneOrMany<TickEvent> | undefined>;
	context: Context;
}): Generator<TickEvent.Phrased[]> {
	const eventsArray = Array.from(events);
	const noteDuration = eventsArray.length;
	const { sustain, dynamic, position } = context.resolvePhrasing({
		noteDuration,
	});

	function attachProps(event: OneOrMany<TickEvent>) {
		return multiMap(
			({
				noteDuration,
				sustain = Sustain.default({ noteDuration }),
				dynamic = Dynamic.default({ noteDuration, sustainDuration: sustain }),
				position = Position.default({ noteDuration, sustainDuration: sustain }),
				event,
			}) => ({ ...event, position, dynamic }),
			{ event, noteDuration, sustain, dynamic, position },
		);
	}

	for (const [index, event] of eventsArray.entries()) {
		if (event) {
			yield applyProps(attachProps(event), index);
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
	props: OneOrMany<TickEvent & Phrasing>,
	index: number,
): TickEvent.Phrased[] {
	return match(props)
		.with(P.when(isMulti), (multiProps) =>
			multiProps.flatMap((prop) => applyProps(prop, index)),
		)
		.with({ error: P._ }, (error) => [error])
		.with({ noteblock: P.nullish }, ({ delay }) => rest(delay))
		.with({ noteblock: P.nonNullable }, ({ position, dynamic, ...note }) =>
			createPhrasedEvents({
				...note,
				position: position[index]!,
				dynamic: dynamic[index]!,
			}),
		)
		.exhaustive();
}

function createPhrasedEvents({
	noteblock,
	delay,
	dynamic,
	position: { level, division },
}: TickEvent<"note"> & EventPhrasing): TickEvent.Phrased[] {
	if (dynamic === 0) {
		return rest(delay);
	}
	if (division === "LR") {
		return times(dynamic).flatMap(() => [
			{ delay, noteblock, level, division: "L" },
			{ delay, noteblock, level, division: "R" },
		]);
	}
	return times(dynamic, () => ({ delay, noteblock, level, division }));
}

function rest(delay: number): TickEvent.Phrased[] {
	return [{ delay, noteblock: undefined }];
}
