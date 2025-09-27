import { resolveDuration } from "#core/resolver/duration.js";
import type { IPositional, Trill as T_Trill } from "#types/schema/@";
import { multiMap, Positional } from "../positional.js";

const Enabled = Positional<T_Trill["enabled"]>({ Default: true });
const Style = Positional<T_Trill["style"]>({ Default: "normal" });
const Start = Positional<T_Trill["start"]>({ Default: 0 });
const End = Positional<T_Trill["end"]>({ Default: "..." });

export class Trill {
	static Default({ noteDuration }: { noteDuration: number }) {
		return {
			enabled: true,
			style: "normal",
			start: 0,
			end: noteDuration,
		};
	}

	private readonly enabled: InstanceType<typeof Enabled>;
	private readonly style: InstanceType<typeof Style>;
	private readonly start: InstanceType<typeof Start>;
	private readonly end: InstanceType<typeof End>;

	constructor(
		args = {
			enabled: new Enabled(),
			style: new Style(),
			start: new Start(),
			end: new End(),
		},
	) {
		this.enabled = args.enabled;
		this.style = args.style;
		this.start = args.start;
		this.end = args.end;
	}

	fork(modifier: IPositional<T_Trill> | undefined) {
		const ctor = this.constructor as new (
			...args: ConstructorParameters<typeof Trill>
		) => this;
		return new ctor({
			enabled: this.enabled.fork(modifier?.enabled),
			style: this.style.fork(modifier?.style),
			start: this.start.fork(modifier?.start),
			end: this.end.fork(modifier?.end),
		});
	}

	transform(modifier: IPositional<T_Trill> | undefined) {
		this.style.transform(modifier?.style);
		this.start.transform(modifier?.start);
		this.end.transform(modifier?.end);
		return this;
	}

	resolve({ beat, noteDuration }: { beat: number; noteDuration: number }) {
		return multiMap(
			({ start, end, ...rest }) => ({
				...rest,
				start: resolveDuration(start, { beat, noteDuration }),
				end: resolveDuration(end, { beat, noteDuration }),
			}),
			{
				enabled: this.enabled.resolve(),
				style: this.style.resolve(),
				start: this.start.resolve(),
				end: this.end.resolve(),
			},
		);
	}
}
