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
} from ".";

export type IStaticProperties = ITime & IDelay & IBeat;

export type IProperties<T = TPosition> = IStaticProperties &
	IInstrument &
	IDynamic &
	ISustain &
	ITranspose &
	ITrill &
	IPosition<T>;
