import { type } from "arktype";
import { re } from "#lib/new-schema/regex.js";
import { timed } from "./duration.js";
import { pitch } from "./pitch.js";

const rest = timed("r");
const single = timed(pitch);
const compound = re.peat(single, options.compound);
const continuous = re.peat(
	re.union(rest, single, compound),
	options.continuous,
);
const parallel = timed(re.peat(single, options.parallel));
const sequential = re.peat(
	re.union(rest, single, compound, continuous, parallel),
	options.sequential,
);

export const noteValue = Object.assign(
	re.union(rest, single, compound, continuous, parallel, sequential),
	{
		rest,
		single,
		compound,
		continuous,
		parallel,
		sequential,
	},
);

export const NoteValue = Object.assign(type(noteValue).brand("NoteValue"), {
	Rest: type(rest).brand("NoteValue.Rest"),
	Single: type(single).brand("NoteValue.Single"),
	Compound: type(compound).brand("NoteValue.Compound"),
	Continuous: type(continuous).brand("NoteValue.Continuous"),
	Parallel: type(parallel).brand("NoteValue.Parallel"),
	Sequential: type(sequential).brand("NoteValue.Sequential"),
});

namespace options {
	export const compound = {
		separator: ";",
		atLeast: 2,
		wrapper: ["<", ">"],
	} as const;
	export const continuous = {
		separator: ";",
		atLeast: 2,
	} as const;
	export const parallel = {
		separator: ";",
		atLeast: 2,
		wrapper: ["\\(", "\\)"],
	} as const;
	export const sequential = {
		separator: ",",
		atLeast: 2,
	} as const;
}
