import type { Re, Repeat, Token } from "#schema/utils/@";
import type { Positional } from "../meta.ts";

export type Instrument = Re<
	Repeat<InstrumentName, { separator: "\\|" }>,
	Re<Token<"\\|">, "null">,
	"?"
>;

export type IInstrument = {
	/**
	 * Multiple instruments can be specified, separated by `|`. The program will try to use the first one, if the note is out of range for that instrument, then the second one, and so on. Error if no instrument can play the note.
	 * "null" is a fictional instrument that plays nothing but fits every note. E.g., "guitar|null" will play guitar if the note fits, else ignore that note.
	 */
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
