import { isEmpty } from "lodash";
import { match, P } from "ts-pattern";
import { splitTimedValue } from "#core/resolver/duration.js";
import { normalize } from "#core/validator/@";
import type { Note, NoteValue } from "#schema/@";
import type { Context } from "../context.js";
import { chain, zip } from "../generator-utils.js";
import type { TickEvent } from "../tick.js";
import { resolveNoteblocks } from "./noteblock.js";
import { applyPhrasing } from "./phrasing.js";

export function resolveNote(
	note: Note,
	voiceContext: Context,
): Generator<TickEvent.Phrased[]> {
	const { trillValue, noteModifier, ...normalizedNote } = normalize(note);

	const noteContext = isEmpty(noteModifier)
		? voiceContext
		: voiceContext.fork(noteModifier);

	function resolveSimple(noteValue: NoteValue.Simple, context = noteContext) {
		const events = resolveNoteblocks({ noteValue, trillValue, context });
		return applyPhrasing({ events, context });
	}

	function resolveChord(noteValue: NoteValue.Chord) {
		const { value: pitches, duration } = splitTimedValue(noteValue);
		return zip(
			pitches
				.slice(1, -1)
				.split(";")
				.filter((v) => v.trim())
				.map((pitch) => (duration ? `${pitch}:${duration}` : pitch))
				.map((v) => resolveSimple(v)),
		);
	}

	function resolveCompound(noteValue: (Note.Simple | Note.Chord)[]) {
		const events = chain(
			noteValue.map((note) => {
				const { value, trillValue, noteModifier } = normalize(note);
				return resolveNoteblocks({
					noteValue: value,
					trillValue,
					context: noteContext.fork(noteModifier),
				});
			}),
		);
		return applyPhrasing({ events, context: noteContext });
	}

	function resolveQuaver(noteValue: NoteValue.Quaver) {
		const { beat } = noteContext.resolveStatic();
		const halfBeat = Math.max(1, Math.floor(beat / 2));
		const fastContext = noteContext.fork({ beat: halfBeat });

		const values = noteValue.split("'");
		const quaverNotes = values
			.slice(0, -1)
			.map((v) => resolveSimple(v, fastContext));

		const lastValue = values[values.length - 1]!;
		if (!lastValue.trim()) {
			return chain(quaverNotes);
		}
		const normalNote = resolveSimple(lastValue);
		return chain([...quaverNotes, normalNote]);
	}

	return match(normalizedNote)
		.with({ type: "simple", value: P.select() }, (v) => resolveSimple(v))
		.with({ type: "chord", value: P.select() }, resolveChord)
		.with({ type: "compound", value: P.select() }, resolveCompound)
		.with({ type: "quaver", value: P.select() }, resolveQuaver)
		.exhaustive();
}
