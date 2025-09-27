import { resolveDuration } from "#core/resolver/duration.js";
import type { IPositional, Trill as T_Trill } from "#types/schema/@";
import { multiMap, Positional } from "../positional.js";

const Style = Positional<T_Trill["style"]>({ Default: "normal" });
const Start = Positional<T_Trill["start"]>({ Default: 0 });
const Length = Positional<T_Trill["length"]>({ Default: "..." });

export class Trill {
	static Default({ noteDuration }: { noteDuration: number }) {
		return { style: "normal" as const, start: 0, length: noteDuration };
	}

	private readonly style: InstanceType<typeof Style>;
	private readonly start: InstanceType<typeof Start>;
	private readonly length: InstanceType<typeof Length>;

	constructor(
		args = { style: new Style(), start: new Start(), length: new Length() },
	) {
		this.style = args.style;
		this.start = args.start;
		this.length = args.length;
	}

	fork(modifier: IPositional<T_Trill> | undefined) {
		const ctor = this.constructor as new (
			...args: ConstructorParameters<typeof Trill>
		) => this;
		return new ctor({
			style: this.style.fork(modifier?.style),
			start: this.start.fork(modifier?.start),
			length: this.length.fork(modifier?.length),
		});
	}

	transform(modifier: IPositional<T_Trill> | undefined) {
		this.style.transform(modifier?.style);
		this.start.transform(modifier?.start);
		this.length.transform(modifier?.length);
		return this;
	}

	resolve({ beat, noteDuration }: { beat: number; noteDuration: number }) {
		return multiMap(
			({ style, start, length }) => ({
				style,
				start: resolveDuration(start, { beat, noteDuration }),
				length: resolveDuration(length, { beat, noteDuration }),
			}),
			{
				style: this.style.resolve(),
				start: this.start.resolve(),
				length: this.length.resolve(),
			},
		);
	}
}
