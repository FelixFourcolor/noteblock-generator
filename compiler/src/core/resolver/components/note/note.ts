import { isEmpty } from "lodash";
import { match, P } from "ts-pattern";
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

	const context = isEmpty(noteModifier)
		? voiceContext
		: voiceContext.fork(noteModifier);

	function resolveSimple(noteValue: NoteValue) {
		const events = resolveNoteblocks({ noteValue, trillValue, context });
		return applyPhrasing({ events, context });
	}

	function resolveCompound(values: Note.Simple[]) {
		const events = chain(
			values.map((note) => {
				const { value, trillValue, noteModifier } = normalize(note);
				return resolveNoteblocks({
					noteValue: value,
					trillValue,
					context: context.fork(noteModifier),
				});
			}),
		);
		return applyPhrasing({ events, context });
	}

	function resolveChord(chordItems: (Note.Single | Note.Compound)[]) {
		return zip(chordItems.map((note) => resolveNote(note, context)));
	}

	return match(normalizedNote)
		.with({ type: "simple", value: P.select() }, resolveSimple)
		.with({ type: "compound", value: P.select() }, resolveCompound)
		.with({ type: "chord", value: P.select() }, resolveChord)
		.exhaustive();
}
