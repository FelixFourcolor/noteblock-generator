import type { Duration, Pitch } from "#lib/schema/types/note/@";
import type { Int } from "#lib/schema/types/utils/@";
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

export type TrillNote =
	| Trill.Value
	| ({ trill: Trill.Value } & Partial<IStatic<Trill>>);
export interface ITrillNote {
	trill?: TrillNote;
}
