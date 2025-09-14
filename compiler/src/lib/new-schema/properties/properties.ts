import { type Type, type } from "arktype";
import { IName } from "./global/name.js";
import { IWidth } from "./global/width.js";
import { IDivision } from "./positional/division.js";
import { IDynamic } from "./positional/dynamic.js";
import { IInstrument } from "./positional/instrument.js";
import { ILevel } from "./positional/level.js";
import { IPosition, type TPosition } from "./positional/position.js";
import { ISustain } from "./positional/sustain.js";
import { ITranspose } from "./positional/transpose.js";
import { IBeat } from "./static/beat.js";
import { IDelay } from "./static/delay.js";
import { ITime } from "./static/time.js";
import { ITrill } from "./static/trill.js";

const IBaseProperties = type.and(
	IWidth,
	IName,
	ITime,
	IBeat,
	IDelay,
	ITrill,
	IInstrument,
	IDynamic,
	ISustain,
	ITranspose,
);
type IBaseProperties = typeof IBaseProperties.t;

export function IProperties<T extends TPosition = TPosition>(t?: T) {
	const IPositionalProperties =
		t === "single"
			? type.or(IPosition("single"), ILevel)
			: type.or(IPosition("double"), type.and(ILevel, IDivision));

	return type.and(IBaseProperties, IPositionalProperties).partial() as Type<
		IProperties<T>
	>;
}

type IPositionalProperties<T extends TPosition> = T extends "single"
	? IPosition<"single"> | ILevel
	: IPosition<"double"> | (ILevel & IDivision);

type Cover<T extends object, Keys extends string> = T extends T
	? T & { [K in Keys]: K extends keyof T ? T[K] : undefined }
	: never;

export type IProperties<T extends TPosition = TPosition> = Partial<
	IBaseProperties &
		Cover<IPositionalProperties<T>, "position" | "level" | "division">
>;
