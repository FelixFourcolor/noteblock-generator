import type { Duration, Pitch } from "#types/schema/note/@";
import type { Int, Modified } from "#types/utils/@";
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

export interface ITrill {
	trill: IPositional<Trill>;
}

export interface INoteTrill {
	trill?: Modified<
		{ value: Trill.Value },
		{ [K in keyof Trill]?: Positional<Trill[K]> }
	>;
}
