import { type } from "arktype";
import { duration } from "#lib/new-schema/note/duration.js";
import { re } from "#lib/new-schema/regex.js";
import { IPositional } from "../meta.js";

const absolute = duration.determinate;
const relative = re("[+-]", re.token(absolute, `"`));

export const sustain = Object.assign(
	re.union(absolute, relative), //
	{ absolute, relative },
);

const Absolute = type
	.or(absolute, "boolean", "number.integer")
	.brand("Sustain.Absolute");
const Relative = type(relative).brand("Sustain.Relative");

export const Sustain = Object.assign(
	type(Absolute, "|", Relative).brand("Sustain"),
	{ Absolute, Relative },
);
export const ISustain = IPositional({ sustain: Sustain });

export type Sustain = typeof Sustain.t;
export type ISustain = typeof ISustain.t;
