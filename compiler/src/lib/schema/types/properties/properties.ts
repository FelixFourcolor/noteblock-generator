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
} from "#lib/schema/types/properties/@";
import type { Cover } from "#lib/schema/types/utils/@";

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

interface positionVariants {
	single: IPosition<"single"> | ILevel;
	double: IPosition<"double"> | (ILevel & IDivision);
}

export type IProperties<T = TPosition> = Partial<
	BaseProperties &
		Cover<
			positionVariants[[T] extends [TPosition] ? T : TPosition],
			"division" | "level" | "position"
		>
>;
