import { resolveDuration } from "#core/resolver/duration.js";
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

	constructor({
		style = new Style(),
		start = new Start(),
		end = new End(),
	}: {
		style?: InstanceType<typeof Style>;
		start?: InstanceType<typeof Start>;
		end?: InstanceType<typeof End>;
	} = {}) {
		this.style = style;
		this.start = start;
		this.end = end;
	}

	fork(modifier: IStatic<T_Trill> | undefined) {
		const ctor = this.constructor as new (
			...args: ConstructorParameters<typeof Trill>
		) => this;
		return new ctor({
			style: this.style.fork(modifier?.style),
			start: this.start.fork(modifier?.start),
			end: this.end.fork(modifier?.end),
		});
	}

	transform(modifier: IStatic<T_Trill> | undefined) {
		this.style.transform(modifier?.style);
		this.start.transform(modifier?.start);
		this.end.transform(modifier?.end);
		return this;
	}

	resolve({ beat, noteDuration }: { beat: number; noteDuration: number }) {
		const style = this.style.resolve();
		const start = this.start.resolve();
		const end = this.end.resolve();

		return {
			trillStyle: style,
			trillStart: resolveDuration(start, { beat, noteDuration }),
			trillEnd: resolveDuration(end, { beat, noteDuration }),
		};
	}
}
