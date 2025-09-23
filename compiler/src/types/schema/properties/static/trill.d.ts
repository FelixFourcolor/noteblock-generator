import type { Duration, Pitch } from "#types/schema/note/@";
import type { Int, Modified } from "#types/utils/@";
import type { IStatic } from "../meta.ts";

export namespace Trill {
	export type Value = boolean | Int<-12, 12> | Pitch;
	export type Style = "normal" | "alt";
}

export type Trill = {
	style: Trill.Style;
	start: Duration.determinate | Int;
	end: Duration | Int;
};

export interface ITrill {
	trill: IStatic<Trill>;
}

export type TrillNote = Modified<
	{ trill: Trill.Value },
	Partial<IStatic<Trill>>
>;

export interface INoteTrill {
	trill?: TrillNote;
}
