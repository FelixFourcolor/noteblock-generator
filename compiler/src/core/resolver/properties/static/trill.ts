import type { IStatic, Trill as T_Trill } from "#types/schema/@";
import { Static } from "../static.js";

const Style = Static<T_Trill["style"]>({ Default: "normal" });
const Start = Static<T_Trill["start"]>({ Default: 0 });
const End = Static<T_Trill["end"]>({ Default: "..." });

export class Trill {
	static readonly default: T_Trill = {
		style: Style.default,
		start: Start.default,
		end: End.default,
	};

	private readonly style: InstanceType<typeof Style>;
	private readonly start: InstanceType<typeof Start>;
	private readonly end: InstanceType<typeof End>;

	constructor(
		style?: InstanceType<typeof Style>,
		start?: InstanceType<typeof Start>,
		end?: InstanceType<typeof End>,
	) {
		this.style = style ?? new Style();
		this.start = start ?? new Start();
		this.end = end ?? new End();
	}

	fork(modifier: IStatic<T_Trill> | undefined) {
		const ctor = this.constructor as new (
			style?: InstanceType<typeof Style>,
			start?: InstanceType<typeof Start>,
			end?: InstanceType<typeof End>,
		) => this;
		return new ctor(
			this.style.fork(modifier?.style),
			this.start.fork(modifier?.start),
			this.end.fork(modifier?.end),
		);
	}

	transform(modifier: IStatic<T_Trill> | undefined) {
		this.style.transform(modifier?.style);
		this.start.transform(modifier?.start);
		this.end.transform(modifier?.end);
		return this;
	}

	resolve(): T_Trill {
		return {
			style: this.style.resolve(),
			start: this.start.resolve(),
			end: this.end.resolve(),
		};
	}
}
