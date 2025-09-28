import type {
	IBeat,
	IDelay,
	IDynamic,
	IInstrument,
	IPosition,
	ISustain,
	ITime,
	ITranspose,
	ITrill,
	TPosition,
} from "#schema/properties/@";

export type IStaticProperties = ITime & IDelay & IBeat;

export type IProperties<T extends TPosition = TPosition> = IStaticProperties &
	IInstrument &
	IDynamic &
	ISustain &
	ITranspose &
	ITrill &
	IPosition<T>;
