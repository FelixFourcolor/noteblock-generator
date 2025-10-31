import { isEmpty } from "lodash";
import { match, P } from "ts-pattern";
import { createIs } from "typia";
import { splitTimedValue } from "#core/resolver/duration.js";
import type { OneOrMany } from "#core/resolver/properties/multi.js";
import type { Note, NoteModifier, NoteValue, Trill } from "#schema/@";
import type { Context } from "../context.js";
import { chain, multiZip, zip } from "../generator-utils.js";
import type { TickEvent } from "../tick.js";
import { resolveNoteblocks } from "./noteblock.js";
import { applyPhrasing } from "./phrasing.js";

type ResolvedNote<Phrased extends boolean = true> = Phrased extends true
	? Generator<TickEvent.Phrased[]>
	: Generator<OneOrMany<TickEvent> | undefined>;

export function resolveNote(note: Note, voiceContext: Context): ResolvedNote {
	const { value, trillValue, noteModifier } = normalize(note);
	const noteContext = voiceContext.fork(noteModifier);
	function resolveSimple<Phrased extends boolean>(
		noteValue: NoteValue.Simple,
		context: Context,
		phrased: Phrased,
	): ResolvedNote<Phrased> {
		const events = resolveNoteblocks({ noteValue, trillValue, context });
		return (
			phrased ? applyPhrasing({ events, context }) : events
		) as ResolvedNote<Phrased>;
	}

	function resolveQuaver<Phrased extends boolean>(
		noteValue: NoteValue.Quaver,
		context: Context,
		phrased: Phrased,
	): ResolvedNote<Phrased> {
		const values = noteValue.split("'");
		const { beat } = noteContext.resolveStatic();
		const halfBeat = Math.max(1, Math.floor(beat / 2));
		const fastContext = context.fork({ beat: halfBeat });

		function resolveItem(value: NoteValue.Quaver.Item, context = noteContext) {
			return match(value)
				.with(P.when(isSimple), (v) => resolveSimple(v, context, false))
				.with(P.when(isChord), (v) => resolveChord(v, context, false))
				.otherwise((value) => {
					throw new Error(`Invalid quaver item: ${value}`);
				});
		}

		const result = values.slice(0, -1).map((v) => resolveItem(v, fastContext));
		const phrasedResult = phrased
			? result.map((events) => applyPhrasing({ events, context: fastContext }))
			: [];

		const lastValue = values[values.length - 1]!;
		if (lastValue.trim()) {
			const lastNote = resolveItem(lastValue);
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

	function resolveChord<Phrased extends boolean>(
		noteValue: NoteValue.Chord,
		context: Context,
		phrased: Phrased,
	): ResolvedNote<Phrased> {
		const { value: pitches, duration } = splitTimedValue(noteValue);
		const chordItems = pitches
			.slice(1, -1)
			.split(";")
			.filter((v) => v.trim())
			.map((pitch) => (duration ? `${pitch}:${duration}` : pitch));

		return (
			phrased
				? zip(chordItems.map((v) => resolveSimple(v, context, true)))
				: multiZip(chordItems.map((v) => resolveSimple(v, context, false)))
		) as ResolvedNote<Phrased>;
	}

	if (typeof value === "string") {
		return match(value)
			.with(P.when(isSimple), (v) => resolveSimple(v, noteContext, true))
			.with(P.when(isChord), (v) => resolveChord(v, noteContext, true))
			.with(P.when(isQuaver), (v) => resolveQuaver(v, noteContext, true))
			.exhaustive();
	}

	const compoundItems = value.map((note) => {
		const { value, noteModifier } = normalize(note);
		const context = noteContext.fork(noteModifier);

		if (Array.isArray(value)) {
			throw new Error(`Invalid compound item: ${JSON.stringify(value)}`);
		}

		return match(value)
			.with(P.when(isSimple), (v) => resolveSimple(v, context, false))
			.with(P.when(isChord), (v) => resolveChord(v, context, false))
			.with(P.when(isQuaver), (v) => resolveQuaver(v, context, false))
			.exhaustive();
	});
	return applyPhrasing({ events: chain(compoundItems), context: noteContext });
}

export function normalize(note: Note): {
	value: NoteValue | Note.Compound.Value;
	trillValue: Trill.Value | undefined;
	noteModifier: NoteModifier;
} {
	if (typeof note === "string" || Array.isArray(note)) {
		return { value: note, trillValue: undefined, noteModifier: {} };
	}

	if ("trill" in note) {
		const { trill, note: value, ...noteModifier } = note;
		if (typeof trill !== "object") {
			return { value, noteModifier, trillValue: trill };
		}

		const { value: trillValue, ...trillModifier } = trill;
		if (isEmpty(trillModifier)) {
			return { value, noteModifier, trillValue };
		}

		const noteModifierWithTrill = { ...noteModifier, trill: trillModifier };
		return { value, noteModifier: noteModifierWithTrill, trillValue };
	}

	const { note: value, ...noteModifier } = note as Note.Simple & object;
	return { value, trillValue: undefined, noteModifier };
}

const isSimple = createIs<NoteValue.Simple>();
const isChord = createIs<NoteValue.Chord>();
const isQuaver = createIs<NoteValue.Quaver>();
