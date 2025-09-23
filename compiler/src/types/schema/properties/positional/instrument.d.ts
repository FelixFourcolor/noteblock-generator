import type { Repeat } from "#types/utils/@";
import type { Positional } from "../meta.ts";

export type Instrument = Repeat<InstrumentName, { separator: "\\|" }>;
export interface IInstrument {
	instrument: Positional<Instrument>;
}

type InstrumentName =
	| "bass"
	| "didgeridoo"
	| "guitar"
	| "banjo"
	| "bit"
	| "harp"
	| "iron_xylophone"
	| "pling"
	| "cow_bell"
	| "flute"
	| "bell"
	| "chime"
	| "xylophone"
	| "basedrum"
	| "hat"
	| "snare";
