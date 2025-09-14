import { type } from "arktype";
import { Modified } from "#lib/new-schema/modified.js";
import { Duration, Pitch } from "#lib/new-schema/note/@";
import { IStatic } from "../meta.js";

const Value = type
	.or("boolean", "-12<=number.integer<=12", Pitch)
	.brand("Trill.Value");
const Style = type('"normal" | "alt"').brand("Trill.Style");

const trill = {
	style: Style,
	start: type.or("number.integer", Duration.Determinate).brand("Trill.Start"),
	end: type.or("number.integer", Duration).brand("Trill.End"),
};

export const Trill = Object.assign(
	type(trill).brand("Trill"), //
	{ Value, Style },
);

const trillModifier = IStatic(trill).partial();
export const ITrill = type({ trill: trillModifier });

export const NoteTrill = Modified({ trill: Trill.Value }, trillModifier);
export const INoteTrill = type({ "trill?": NoteTrill });

export type Trill = typeof Trill.t;
export type ITrill = typeof ITrill.t;
export type NoteTrill = typeof NoteTrill.t;
export type INoteTrill = typeof INoteTrill.t;
