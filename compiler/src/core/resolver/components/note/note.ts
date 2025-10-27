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

	function resolveChord(noteValue: NoteValue.Chord, context = noteContext) {
		const { value: pitches, duration } = splitTimedValue(noteValue);
		return zip(
			pitches
				.slice(1, -1)
				.split(";")
				.filter((v) => v.trim())
				.map((pitch) => (duration ? `${pitch}:${duration}` : pitch))
				.map((v) => resolveSimple(v, context)),
		);
	}

	function resolveCompound(values: (Note.Simple | Note.Chord)[]) {
		const events = chain(
			values.map((note) => {
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

	function resolveQuaver(values: NoteValue.Quaver.Item[]) {
		const { beat } = noteContext.resolveStatic();
		const halfBeat = Math.max(1, Math.floor(beat / 2));
		const fastContext = noteContext.fork({ beat: halfBeat });

		function resolveItem(value: NoteValue.Quaver.Item, context?: Context) {
			const type = value.trim().startsWith("(") ? "chord" : "simple";
			if (type === "chord") {
				return resolveChord(value as unknown as NoteValue.Chord, context);
			}
			return resolveSimple(value as unknown as NoteValue.Simple, context);
		}

		const quaverNotes = values
			.slice(0, -1)
			.map((v) => resolveItem(v, fastContext));

		const lastValue = values[values.length - 1]!;
		if (!lastValue.trim()) {
			return chain(quaverNotes);
		}
		const normalNote = resolveItem(lastValue);
		return chain([...quaverNotes, normalNote]);
	}

	return match(normalizedNote)
		.with({ type: "simple", value: P.select() }, (v) => resolveSimple(v))
		.with({ type: "chord", value: P.select() }, (v) => resolveChord(v))
		.with({ type: "compound", value: P.select() }, resolveCompound)
		.with({ type: "quaver", value: P.select() }, resolveQuaver)
		.exhaustive();
}
