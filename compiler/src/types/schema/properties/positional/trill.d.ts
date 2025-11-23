import type { Duration } from "#schema/duration.js";
import type { Pitch } from "#schema/note/@";
import type { Int, Modified } from "#types/helpers/@";
import type { IPositional, Positional } from "../meta.js";

export namespace Trill {
	export type Value = boolean | Int<-12, 12> | Pitch;
	export type Style = "normal" | "alt";
}

export type Trill = {
	style: Trill.Style;
	start: Duration.determinate | Int;
	length: Duration | Int;
};

export type ITrill = { trill?: IPositional<Trill> };

export type INoteTrill = {
	trill?: Modified<
		{ value: Trill.Value },
		{ [K in keyof Trill]?: Positional<Trill[K]> }
	>;
};
