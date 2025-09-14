import { type } from "arktype";
import { re } from "#lib/new-schema/regex.js";
import { IPositional } from "../meta.js";
import { timedSequence } from "./timed-sequence.js";

const number = type("number.integer >= 0");
const uniformAbsolute = re("\\d+");
const uniformRelative = re("[+-]", re.token(uniformAbsolute));

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
			re.token(re.union(uniform.relative, "~")),
			timedSequence(re.union(uniform, "~")),
		),
	},
);

export const level = Object.assign(
	re.union(uniform, variable), //
	{ uniform, variable },
);

export const Level = Object.assign(type(level, "|", number).brand("Level"), {
	Uniform: Object.assign(type(uniform, "|", number).brand("Level.Uniform"), {
		Absolute: type(uniform.absolute, "|", number).brand(
			"Level.Uniform.Absolute",
		),
		Relative: type(uniform.relative).brand("Level.Uniform.Relative"),
	}),
	Variable: Object.assign(type(variable).brand("Level.Variable"), {
		Absolute: type(variable.absolute).brand("Level.Variable.Absolute"),
		Relative: type(variable.relative).brand("Level.Variable.Relative"),
	}),
});

export const ILevel = IPositional({ level: Level });

export type Level = typeof Level.t;
export type ILevel = typeof ILevel.t;
