import { type } from "arktype";
import { re } from "#lib/new-schema/regex.js";
import { IPositional } from "../meta.js";
import { timedSequence } from "./timed-sequence.js";

const uniformAbsolute = re.union("L", "R", "LR");
const uniformRelative = re("SW");

const uniform = Object.assign(re.union(uniformAbsolute, uniformRelative), {
	absolute: uniformAbsolute,
	relative: uniformRelative,
});

const variable = Object.assign(timedSequence(re.union(uniform, "~")), {
	absolute: timedSequence(uniform.absolute),
	relative: re.and(
		re.token(re.union(uniform.relative, "~")),
		timedSequence(re.union(uniform, "~")),
	),
});

export const division = Object.assign(re.union(uniform, variable), {
	uniform,
	variable,
});

export const Division = Object.assign(type(division).brand("Division"), {
	Uniform: Object.assign(type(uniform).brand("Division.Uniform"), {
		Absolute: type(uniform.absolute).brand("Division.Uniform.Absolute"),
		Relative: type(uniform.relative).brand("Division.Uniform.Relative"),
	}),
	Variable: Object.assign(type(variable).brand("Division.Variable"), {
		Absolute: type(variable.absolute).brand("Division.Variable.Absolute"),
		Relative: type(variable.relative).brand("Division.Variable.Relative"),
	}),
});
export const IDivision = IPositional({ division: Division });

export type Division = typeof Division.t;
export type IDivision = typeof IDivision.t;
