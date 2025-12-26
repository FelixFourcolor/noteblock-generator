import { isEmpty } from "lodash";
import { match, P } from "ts-pattern";
import { createIs } from "typia";
import { type OneOrMany, splitTimedValue } from "@/core/resolver/properties";
import type { Note, NoteModifier, NoteValue, Trill } from "@/types/schema";
import type { Context } from "../context";
import type { TickEvent } from "../tick";
import { chain, multiZip, zip } from "../utils/generators";
import { resolveNoteblocks } from "./noteblock";
import { applyPhrasing } from "./phrasing";

type ResolvedNote<Phrased extends boolean = true> = Phrased extends true
	? Generator<TickEvent.Phrased[]>
	: Generator<OneOrMany<TickEvent> | undefined>;

export function resolveNote(note: Note, voiceContext: Context): ResolvedNote {
	const { noteValue, trillValue, noteModifier } = normalize(note);
	const context = voiceContext.fork(noteModifier);

	return match(noteValue)
		.with(isSimple, (v) => resolveSimple(v, trillValue, context))
		.with(isChord, (v) => resolveChord(v, context))
		.with(isQuaver, (v) => resolveQuaver(v, context))
		.with(isSlur, (v) => resolveSlur(v, context))
		.exhaustive();
}

function resolveSimple<Phrased extends boolean = true>(
	noteValue: NoteValue.Simple,
	trillValue: Trill.Value | undefined,
	context: Context,
	phrased: Phrased = true as Phrased,
): ResolvedNote<Phrased> {
	const events = resolveNoteblocks({ noteValue, trillValue, context });
	return (
		phrased ? applyPhrasing({ events, context }) : events
	) as ResolvedNote<Phrased>;
}

function resolveQuaver<Phrased extends boolean = true>(
	noteValue: NoteValue.Quaver,
	context: Context,
	phrased: Phrased = true as Phrased,
): ResolvedNote<Phrased> {
	const values = noteValue.split("'");
	const { beat } = context.resolveStatic();
	const halfBeat = Math.max(1, Math.floor(beat / 2));
	const fastContext = context.fork({ beat: halfBeat });

	function resolveItem(value: string, context: Context) {
		return match(value)
			.with(isSimple, (v) => resolveSimple(v, undefined, context, false))
			.with(isChord, (v) => resolveChord(v, context, false))
			.exhaustive();
	}

	const result = values.slice(0, -1).map((v) => resolveItem(v, fastContext));
	const phrasedResult = phrased
		? result.map((events) => applyPhrasing({ events, context: fastContext }))
		: [];

	const lastValue = values[values.length - 1]!;
	if (lastValue.trim()) {
		const lastNote = resolveItem(lastValue, context);
		result.push(lastNote);
		if (phrased) {
			const phrasedLastNote = applyPhrasing({ events: lastNote, context });
			phrasedResult.push(phrasedLastNote);
		}
	}

	return (
		phrased ? chain(phrasedResult) : chain(result)
	) as ResolvedNote<Phrased>;
}

function resolveChord<Phrased extends boolean = true>(
	noteValue: NoteValue.Chord,
	context: Context,
	phrased: Phrased = true as Phrased,
): ResolvedNote<Phrased> {
	const { value: pitches, duration } = splitTimedValue(noteValue);
	const notes = pitches
		.slice(1, -1)
		.split(";")
		.filter((v) => v.trim())
		.map((pitch) => (duration ? `${pitch}:${duration}` : pitch));

	return (
		phrased
			? zip(notes.map((v) => resolveSimple(v, undefined, context, true)))
			: multiZip(notes.map((v) => resolveSimple(v, undefined, context, false)))
	) as ResolvedNote<Phrased>;
}

function resolveSlur(noteValue: NoteValue.Slur, context: Context) {
	const notes = noteValue
		.split("--")
		.filter((v) => v.trim())
		.map((item) => {
			return match(item)
				.with(isSimple, (v) => resolveSimple(v, undefined, context, false))
				.with(isChord, (v) => resolveChord(v, context, false))
				.with(isQuaver, (v) => resolveQuaver(v, context, false))
				.exhaustive();
		});

	return applyPhrasing({ events: chain(notes), context });
}

function normalize(note: Note): {
	noteValue: NoteValue;
	trillValue: Trill.Value | undefined;
	noteModifier: NoteModifier;
} {
	if (typeof note === "string") {
		return { noteValue: note, trillValue: undefined, noteModifier: {} };
	}

	if ("trill" in note) {
		const { trill, note: noteValue, ...noteModifier } = note;
		if (typeof trill !== "object") {
			return { noteValue, noteModifier, trillValue: trill };
		}

		const { value: trillValue, ...trillModifier } = trill;
		if (isEmpty(trillModifier)) {
			return { noteValue, noteModifier, trillValue };
		}

		const noteModifierWithTrill = { ...noteModifier, trill: trillModifier };
		return {
			noteValue,
			noteModifier: noteModifierWithTrill,
			trillValue,
		};
	}

	const { note: noteValue, ...noteModifier } = note;
	return { noteValue, trillValue: undefined, noteModifier };
}

const isSimple = P.when(createIs<NoteValue.Simple>());
const isChord = P.when(createIs<NoteValue.Chord>());
const isQuaver = P.when(createIs<NoteValue.Quaver>());
const isSlur = P.when(createIs<NoteValue.Slur>());
