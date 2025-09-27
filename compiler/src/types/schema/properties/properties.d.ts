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

export type IStaticProperties = Partial<ITime & IDelay & IBeat>;

export type IPositionalProperties<T extends TPosition = TPosition> =
	IStaticProperties &
		Partial<
			IInstrument & IDynamic & ISustain & ITranspose & ITrill & IPosition<T>
		>;

export type IProperties<T extends TPosition = TPosition> =
	IPositionalProperties<T> & Partial<IName & IWidth>;
