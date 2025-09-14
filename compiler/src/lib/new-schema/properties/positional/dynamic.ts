import { type } from "arktype";
import { re } from "#lib/new-schema/regex.js";
import { IPositional } from "../meta.js";
import { timedSequence } from "./timed-sequence.js";

const number = type("0 <= number.integer <= 6");
const uniformAbsolute = re("[0-6]");
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
			re.token(re.union(uniform.relative, "~"), "."),
			timedSequence(re.union(uniform, "~")),
		),
	},
);

export const dynamic = Object.assign(
	re.union(uniform, variable), //
	{ uniform, variable },
);

export const Dynamic = Object.assign(
	type(dynamic, "|", number).brand("Dynamic"),
	{
		Uniform: Object.assign(
			type(uniform, "|", number).brand("Dynamic.Uniform"),
			{
				Absolute: type(uniform.absolute, "|", number).brand(
					"Dynamic.Uniform.Absolute",
				),
				Relative: type(uniform.relative).brand("Dynamic.Uniform.Relative"),
			},
		),
		Variable: Object.assign(type(variable).brand("Dynamic.Variable"), {
			Absolute: type(variable.absolute).brand("Dynamic.Variable.Absolute"),
			Relative: type(variable.relative).brand("Dynamic.Variable.Relative"),
		}),
	},
);
export const IDynamic = IPositional({ dynamic: Dynamic });

export type Dynamic = typeof Dynamic.t;
export type IDynamic = typeof IDynamic.t;
