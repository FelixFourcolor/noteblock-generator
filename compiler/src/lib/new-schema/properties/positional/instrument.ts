import { type } from "arktype";
import { re } from "#lib/new-schema/regex.js";
import { IPositional } from "../meta.js";

const name = re.union(
	"bass",
	"didgeridoo",
	"guitar",
	"banjo",
	"bit",
	"harp",
	"iron_xylophone",
	"pling",
	"cow_bell",
	"flute",
	"bell",
	"chime",
	"xylophone",
	"basedrum",
	"hat",
	"snare",
);
export const instrument = Object.assign(
	re.peat(name, { atLeast: 1, separator: "\\|" }),
	{ name },
);

export const Instrument = type(instrument).brand("Instrument");
export const IInstrument = IPositional({ instrument: Instrument });

export type Instrument = typeof Instrument.t;
export type IInstrument = typeof IInstrument.t;
