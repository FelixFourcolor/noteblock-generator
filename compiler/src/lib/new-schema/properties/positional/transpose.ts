import { type } from "arktype";
import { re } from "#lib/new-schema/regex.js";
import { IPositional, Positional } from "../meta.js";

export const transpose = {
	value: { relative: re("[+-]", re.token("\\d+")) },
};

const Absolute = type("number.integer").brand("Transpose.Value.Absolute");
const Relative = type(transpose.value.relative).brand(
	"Transpose.Value.Relative",
);

const Value = Object.assign(
	type(Absolute, "|", Relative), //
	{ Absolute, Relative },
);
const Auto = type("boolean").brand("Transpose.Auto");

export const Transpose = Object.assign(
	type({ value: Value, auto: Auto }), //
	{ Value, Auto },
);

export const ITranspose = type({
	transpose: type.or(
		Positional(Value),
		IPositional({ value: Value, auto: Auto }),
	),
});

export type Transpose = typeof Transpose.t;
export type ITranspose = typeof ITranspose.t;
