import type {
	IBeat,
	IDelay,
	IDivision,
	IDynamic,
	IInstrument,
	ILevel,
	IName,
	IPosition,
	ISustain,
	ITime,
	ITranspose,
	ITrill,
	IWidth,
	TPosition,
} from "#types/schema/properties/@";
import type { Cover } from "#types/utils/@";

interface BaseProperties
	extends IName,
		IWidth,
		ITime,
		IDelay,
		IBeat,
		IInstrument,
		IDynamic,
		ISustain,
		ITranspose,
		ITrill {}

type IPositionProperties<T> = Cover<
	T extends "single"
		? IPosition<"single"> | ILevel
		: IPosition<"double"> | (ILevel & IDivision),
	"division" | "level" | "position"
>;

export type IProperties<T = TPosition> = Partial<
	BaseProperties & IPositionProperties<T>
>;
