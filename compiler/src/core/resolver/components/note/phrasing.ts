import { times } from "lodash";
import { match, P } from "ts-pattern";
import type { OneOrMany } from "#core/resolver/properties/@";
import {
	Dynamic,
	isMulti,
	multiMap,
	type NoteBlock,
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
	const { sustain, dynamic, position } = context.resolve({ noteDuration });

	function bindProps(note: TickEvent<"note">): OneOrMany<{
		noteblock: NoteBlock | undefined;
		delay: number;
		position: { level: number; division: "L" | "R" | "LR" }[];
		dynamic: number[];
	}> {
		return multiMap(
			({
				noteDuration,
				sustain = Sustain.default({ noteDuration }),
				dynamic = Dynamic.default({ noteDuration, sustainDuration: sustain }),
				position = Position.default({
					noteDuration,
					sustainDuration: sustain,
				}),
				...note
			}) => ({ ...note, position, dynamic }),
			{ ...note, noteDuration, sustain, dynamic, position },
		);
	}

	function apply(args: {
		event: OneOrMany<TickEvent> | undefined;
		index: number;
	}): TickEvent.Phrased[] {
		const { event, index } = args;
		return match(event)
			.with(undefined, () => [])
			.with(P.when(isMulti), () => multiMap(apply, args).flat())
			.with({ noteblock: P.nonNullable }, (note) =>
				applyProps(bindProps(note), index),
			)
			.otherwise((nonNote) => [nonNote]);
	}

	for (const [index, event] of eventsArray.entries()) {
		yield apply({ event, index });
	}
}

function applyProps(
	props: OneOrMany<{
		noteblock: NoteBlock | undefined;
		delay: number;
		position: { level: number; division: "L" | "R" | "LR" }[];
		dynamic: number[];
	}>,
	index: number,
): TickEvent.Phrased[] {
	return match(props)
		.with(P.when(isMulti), (multiProps) =>
			multiProps.flatMap((prop) => applyProps(prop, index)),
		)
		.with({ noteblock: P.nullish }, (rest) => [rest])
		.with({ noteblock: P.nonNullable }, ({ position, dynamic, ...note }) =>
			createPhrasedEvents({
				...note,
				position: position[index]!,
				dynamic: dynamic[index]!,
			}),
		)
		.exhaustive();
}

function createPhrasedEvents(args: {
	noteblock: NoteBlock;
	delay: number;
	dynamic: number;
	position: { level: number; division: "L" | "R" | "LR" };
}): TickEvent.Phrased[] {
	return match(args)
		.with({ dynamic: 0 }, ({ delay }) => [{ delay }])
		.with({ position: { division: "LR" } }, ({ dynamic, position, ...note }) =>
			times(dynamic).flatMap(() => [
				{ ...note, ...position, division: "L" },
				{ ...note, ...position, division: "R" },
			]),
		)
		.otherwise(({ dynamic, position, ...note }) =>
			times(dynamic, () => ({ ...note, ...position })),
		);
}
