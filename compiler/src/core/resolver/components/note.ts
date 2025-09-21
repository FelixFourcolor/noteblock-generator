import { isEmpty } from "lodash";
import { match, P } from "ts-pattern";
import { createIs } from "typia";
import { splitTimedValue } from "#core/resolver/duration.js";
import type {
	Chord,
	IProperties,
	IStatic,
	Note,
	NoteValue,
	Trill,
} from "#core/types/@";
import type { Context } from "./context.js";
import { chain, zip } from "./generator-utils.js";
import { resolveNoteblocks } from "./noteblock.js";
import { applyPhrasing, type PhrasedEvent } from "./phrasing.js";

export function resolveChord(
	chord: Chord,
	context: Context,
): Generator<PhrasedEvent[]> {
	let notes: Note[];
	if ("note" in chord) {
		const { note, ...chordModifier } = chord;
		notes = note;
		if (!isEmpty(chordModifier)) {
			context = context.fork(chordModifier);
		}
	} else {
		notes = chord;
	}
	return zip(notes.map((note) => resolveNote(note, context)));
}

export function resolveNote(
	note: Note,
	voiceContext: Context,
): Generator<PhrasedEvent[]> {
	const { noteValue, trillValue, noteModifier } = normalize(note);
	const context = voiceContext.fork(noteModifier);

	function resolveSimple(noteValue: NoteValue.Simple, ctx: Context = context) {
		return applyPhrasing({
			noteEvents: resolveNoteblocks({ noteValue, trillValue, context: ctx }),
			context: ctx,
		});
	}

	function resolveContinuous(noteValue: NoteValue.Continuous) {
		const sustainedCtx = context.fork({ sustain: true });

		const values = noteValue.split(/;(?![^<]*[>])/).map((v) => v.trim());
		console.error({ values });
		const initialNotes = chain(
			values.slice(0, -1).map((value) => resolveSimple(value, sustainedCtx)),
		);
		const lastNote = resolveSimple(values[values.length - 1]!);

		return chain([initialNotes, lastNote]);
	}

	function resolveVariableParallel(noteValue: NoteValue.Parallel.variable) {
		return zip(
			noteValue
				.trim()
				.slice(1, -1) // remove wrappers
				.split(";")
				.map((value) => resolveSimple(value)),
		);
	}

	function resolveUniformParallel(noteValue: NoteValue.Parallel.uniform) {
		const { value: pitches, duration } = splitTimedValue(noteValue);
		return zip(
			pitches
				.slice(1, -1) // remove wrappers
				.split(";")
				.map((pitch) => (duration ? `${pitch}:${duration}` : pitch))
				.map((value) => resolveSimple(value)),
		);
	}

	function resolveSequential(noteValue: NoteValue.Sequential) {
		return chain(noteValue.split(",").map(resolveNonSequential));
	}

	function resolveNonSequential(
		noteValue: Exclude<NoteValue, NoteValue.Sequential>,
	) {
		return match(noteValue)
			.with(P.when(createIs<NoteValue.Simple>()), (note) => resolveSimple(note))
			.with(P.when(createIs<NoteValue.Continuous>()), resolveContinuous)
			.with(
				P.when(createIs<NoteValue.Parallel.variable>()),
				resolveVariableParallel,
			)
			.with(
				P.when(createIs<NoteValue.Parallel.uniform>()),
				resolveUniformParallel,
			)
			.exhaustive();
	}

	return match(noteValue)
		.with(P.when(createIs<NoteValue.Sequential>()), resolveSequential)
		.otherwise(resolveNonSequential);
}

function normalize(note: Note): {
	noteValue: NoteValue;
	trillValue: Trill.Value | undefined;
	noteModifier: Partial<IProperties>;
} {
	if (typeof note === "string") {
		return { noteValue: note, trillValue: undefined, noteModifier: {} };
	}

	if (!("trill" in note)) {
		const { note: noteValue, ...noteModifier } = note;
		return {
			noteValue,
			trillValue: undefined,
			noteModifier: noteModifier as Partial<IProperties>,
		};
	}

	const { trill, note: noteValue, ...noteModifier } = note;
	if (typeof trill !== "object") {
		return { noteValue, trillValue: trill, noteModifier };
	}
	const { trill: trillValue, ...trillModifier } = trill;
	if (isEmpty(trillModifier)) {
		return { noteValue, trillValue, noteModifier };
	}
	return {
		noteValue,
		trillValue,
		noteModifier: { ...noteModifier, trill: trillModifier as IStatic<Trill> },
	};
}
