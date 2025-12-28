import type {
	IBeat,
	IDelay,
	IDynamic,
	IInstrument,
	IPosition,
	IPreset,
	ISustain,
	ITime,
	ITranspose,
	ITrill,
	TPosition,
} from ".";

export type IStaticProperties = ITime & IDelay & IBeat;

export type IPositionalProperties<T = TPosition> = IInstrument &
	IDynamic &
	ISustain &
	ITranspose &
	ITrill &
	IPosition<T>;

export type IProperties<T = TPosition> = IPreset<T> &
	IStaticProperties &
	IPositionalProperties<T>;
