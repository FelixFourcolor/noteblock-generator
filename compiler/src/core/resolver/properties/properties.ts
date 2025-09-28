import { is } from "typia";
import {
	Beat,
	Delay,
	Dynamic,
	Instrument,
	Name,
	Position,
	Sustain,
	Time,
	Transpose,
	Trill,
	Width,
} from "#core/resolver/properties/@";
import type {
	IGlobalProperties,
	IName,
	IPositionalProperties,
	Pitch,
	Positional,
	Transpose as T_Transpose,
	Trill as T_Trill,
} from "#types/schema/@";
import type { OneOrMany } from "./multi.js";
import type { PositionalClass } from "./positional.js";
import type { StaticClass } from "./static.js";

export type ResolveType<T> = T extends StaticClass<infer U>
	? U
	: T extends PositionalClass<any, any, any, infer U>
		? U | undefined
		: T extends new (
					...args: any
				) => { resolve: (...args: any) => infer U }
			? U extends OneOrMany<infer V>
				? V | undefined
				: never
			: never;

export class Properties {
	protected name: Name;
	protected width = new Width();
	protected beat = new Beat();
	protected delay = new Delay();
	protected time = new Time();
	protected trill = new Trill();
	protected dynamic = new Dynamic();
	protected sustain = new Sustain();
	protected transpose = new Transpose();
	protected instrument = new Instrument();
	protected position = new Position();

	get level() {
		return this.position.level;
	}
	get division() {
		return this.position.division;
	}

	constructor({ name }: IName = {}) {
		this.name = new Name(name);
	}

	transform(modifier: IPositionalProperties): this {
		this.beat.transform(modifier.beat);
		this.delay.transform(modifier.delay);
		this.time.transform(modifier.time);
		this.trill.transform(modifier.trill);
		this.instrument.transform(modifier.instrument);

		const beat = this.beat.resolve();

		this.level.transform(modifier.level, { beat });
		this.division.transform(modifier.division, { beat });
		this.position.transform(modifier.position, { beat });
		this.dynamic.transform(modifier.dynamic, { beat });
		this.sustain.transform(modifier.sustain, { beat });

		if (modifier.transpose !== undefined) {
			if (is<Positional<T_Transpose.Value>>(modifier.transpose)) {
				this.transpose.transform({ value: modifier.transpose });
			} else {
				this.transpose.transform(modifier.transpose);
			}
		}

		return this;
	}

	fork(modifier: IGlobalProperties): Properties {
		const forked = new Properties();

		forked.beat = this.beat.fork(modifier.beat);
		forked.delay = this.delay.fork(modifier.delay);
		forked.time = this.time.fork(modifier.time);
		forked.trill = this.trill.fork(modifier.trill);
		forked.instrument = this.instrument.fork(modifier.instrument);

		forked.name = this.name.fork(modifier.name);
		forked.width = this.width.fork({ time: forked.time.resolve() });

		if (is<Positional<T_Transpose.Value>>(modifier.transpose)) {
			forked.transpose = this.transpose.fork({ value: modifier.transpose });
		} else {
			forked.transpose = this.transpose.fork(modifier.transpose);
		}

		const beat = this.beat.resolve();

		forked.dynamic = this.dynamic.fork(modifier.dynamic, { beat });
		forked.sustain = this.sustain.fork(modifier.sustain, { beat });

		if (modifier.position !== undefined) {
			forked.position = this.position.fork(modifier.position, { beat });
		} else {
			const level = this.level.fork(modifier.level, { beat });
			const division = this.division.fork(modifier.division, { beat });
			forked.position = new Position({ level, division });
		}

		return forked;
	}

	resolveStatic() {
		return {
			beat: this.beat.resolve(),
			delay: this.delay.resolve(),
			time: this.time.resolve(),
		};
	}

	resolveGlobals() {
		return {
			name: this.name.resolve(),
			width: this.width.resolve(),
		};
	}

	resolveTrill({ noteDuration }: { noteDuration: number }) {
		const beat = this.beat.resolve();
		return this.trill.resolve({ noteDuration, beat });
	}

	resolvePhrasing({ noteDuration }: { noteDuration: number }) {
		const sustainDuration = this.sustain.resolve({ noteDuration });
		const position = this.position.resolve({
			noteDuration,
			sustain: sustainDuration,
		});
		const dynamic = this.dynamic.resolve({
			noteDuration,
			sustain: sustainDuration,
		});
		return {
			sustain: sustainDuration,
			position,
			dynamic,
		};
	}

	resolveInstrument(args: {
		pitch: Pitch;
		trillValue: T_Trill.Value | undefined;
	}) {
		const transpose = this.transpose.resolve();
		return this.instrument.resolve({ ...args, ...transpose });
	}
}
