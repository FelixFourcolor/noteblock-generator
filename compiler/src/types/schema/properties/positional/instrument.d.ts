import type { Re, Repeat, Token } from "@/types/helpers";
import type { Positional } from "../meta";

export type Instrument = Re<
	Repeat<InstrumentName, { separator: "\\|" }>,
	Re<Token<"\\|">, "null">,
	"?"
>;

export type IInstrument = {
	instrument?: Positional<Instrument>;
};

export type InstrumentName =
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
	| "xylophone";
