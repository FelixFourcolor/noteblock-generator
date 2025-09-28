import type {
	IBeat,
	IDelay,
	IDynamic,
	IInstrument,
	IName,
	IPosition,
	ISustain,
	ITime,
	ITranspose,
	ITrill,
	IWidth,
	TPosition,
} from "#types/schema/properties/@";

export type IStaticProperties = ITime & IDelay & IBeat;

export type IPositionalProperties<T extends TPosition = TPosition> =
	IStaticProperties &
		IInstrument &
		IDynamic &
		ISustain &
		ITranspose &
		ITrill &
		IPosition<T>;

export type IGlobalProperties<T extends TPosition = TPosition> =
	IPositionalProperties<T> & IName & IWidth;
