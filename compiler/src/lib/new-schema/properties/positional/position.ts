import { type Type, type } from "arktype";
import { re } from "#lib/new-schema/regex.js";
import { IPositional } from "../meta.js";
import { division } from "./division.js";
import { Level, level } from "./level.js";
import { timedSequence } from "./timed-sequence.js";

const uniformAbsolute = re.union(
	division.uniform.absolute,
	level.uniform.absolute,
	re(division.uniform.absolute, "\\s*", level.uniform.absolute),
);
const uniformRelative = re.union(
	re(re.token(division.uniform), "?", level.uniform.relative),
	re(division.uniform.relative, re.token(level.uniform), "?"),
);

const uniform = Object.assign(
	re.union(uniformAbsolute, uniformRelative), //
	{
		absolute: uniformAbsolute,
		relative: uniformRelative,
	},
);

const variable = Object.assign(
	timedSequence(re.union(uniform, "~")), //
	{
		absolute: timedSequence(uniform.absolute),
		relative: re.and(
			re.token(re.union(uniform.relative, "~"), "."),
			timedSequence(re.union(uniform, "~")),
		),
	},
);

export const position = Object.assign(
	re.union(uniform, variable), //
	{ uniform, variable },
);

export const Position = Object.assign(type(position).brand("Position"), {
	Uniform: Object.assign(type(uniform).brand("Position.Uniform"), {
		Absolute: type(uniform.absolute).brand("Position.Uniform.Absolute"),
		Relative: type(uniform.relative).brand("Position.Uniform.Relative"),
	}),
	Variable: Object.assign(type(variable).brand("Position.Variable"), {
		Absolute: type(variable.absolute).brand("Position.Variable.Absolute"),
		Relative: type(variable.relative).brand("Position.Variable.Relative"),
	}),
});

const ISinglePosition = IPositional({ position: Level });
const IDoublePosition = IPositional({ position: Position });

export function IPosition<const T extends TPosition = "double">(type?: T) {
	return (type === "single" ? ISinglePosition : IDoublePosition) as Type<
		IPosition<T>
	>;
}

export type TPosition = "single" | "double";
export type Position = typeof Position.t;
export type IPosition<T extends TPosition = "double"> = T extends "single"
	? typeof ISinglePosition.t
	: typeof IDoublePosition.t;
