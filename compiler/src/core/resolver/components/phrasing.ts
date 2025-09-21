import { times } from "lodash";
import { match, P } from "ts-pattern";
import type { Multi, OneOrMany } from "#core/resolver/properties/@";
import {
	Dynamic,
	isMulti,
	multiMap,
	type NoteBlock,
	Position,
	Sustain,
} from "#core/resolver/properties/@";
import type { Context } from "./context.js";
import type { BlockEvent, TEvent } from "./noteblock.js";

type Placement = { level: number; division: "L" | "R" };

export type PhrasedEvent<T extends TEvent = TEvent> = T extends "note"
	? BlockEvent<T> & Placement
	: BlockEvent<T>;

export function* applyPhrasing({
	noteEvents,
	context,
}: {
	noteEvents: Generator<OneOrMany<BlockEvent> | undefined>;
	context: Context;
}): Generator<PhrasedEvent[]> {
	const events = Array.from(noteEvents);
	const noteDuration = events.length;
	const { sustain, dynamic, position } = context.resolve({ noteDuration });

	const bindProps = (
		note: BlockEvent<"note">,
	): OneOrMany<{
		noteblock: NoteBlock | undefined;
		delay: number;
		position: { level: number; division: "L" | "R" | "LR" }[];
		dynamic: number[];
	}> =>
		multiMap(
			({
				noteDuration,
				sustain = Sustain.default({ noteDuration }),
				dynamic = Dynamic.default({ noteDuration, sustainDuration: sustain }),
				position = Position.default({ noteDuration, sustainDuration: sustain }),
				...note
			}) => ({ ...note, position, dynamic }),
			{ ...note, noteDuration, sustain, dynamic, position },
		);

	const apply = ({
		event,
		index,
	}: {
		event: OneOrMany<BlockEvent> | undefined;
		index: number;
	}): PhrasedEvent[] =>
		match(event)
			.with(undefined, () => [])
			.with(P.when(isMulti), (event: Multi<BlockEvent>) =>
				multiMap(apply, { event, index }).flat(),
			)
			.with({ noteblock: P.nonNullable }, (note) =>
				applyProps(bindProps(note), index),
			)
			.otherwise((nonNote) => [nonNote]);

	for (const [index, event] of events.entries()) {
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
): PhrasedEvent[] {
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
}): PhrasedEvent<"note" | "rest">[] {
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
