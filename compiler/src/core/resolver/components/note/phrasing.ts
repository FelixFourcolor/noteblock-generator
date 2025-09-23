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

	function attachProps(event: OneOrMany<TickEvent>) {
		const note = multiMap(getNote, { event });
		const args = { note, noteDuration, sustain, dynamic, position };
		return multiMap(
			({
				noteDuration,
				sustain = Sustain.default({ noteDuration }),
				dynamic = Dynamic.default({ noteDuration, sustainDuration: sustain }),
				position = Position.default({ noteDuration, sustainDuration: sustain }),
				note,
			}) => ({ ...note, position, dynamic }),
			args,
		);
	}

	for (const [index, event] of eventsArray.entries()) {
		if (!event) {
			yield [];
			continue;
		}
		yield applyProps(attachProps(event), index);
	}
}

function getNote({ event }: { event: TickEvent }) {
	return match(event)
		.with({ error: P._ }, () => ({
			delay: 1, // delay doesn't matter when error
			noteblock: undefined,
		}))
		.otherwise((note) => note);
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
		.with({ dynamic: 0 }, ({ delay }) => [{ delay, noteblock: undefined }])
		.with({ position: { division: "LR" } }, ({ dynamic, position, ...note }) =>
			times(dynamic).flatMap(() => [
				{ ...note, ...position, division: "L" as const },
				{ ...note, ...position, division: "R" as const },
			]),
		)
		.otherwise(({ dynamic, position: { level, division }, ...note }) =>
			times(dynamic, () => ({
				...note,
				level,
				division: division as "L" | "R", // ts-pattern's narrowing not working
			})),
		);
}
