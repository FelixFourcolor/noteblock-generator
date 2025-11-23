import { is } from "typia";
import {
	Beat,
	Delay,
	Dynamic,
	Instrument,
	Position,
	Sustain,
	Time,
	Transpose,
	Trill,
} from "#core/resolver/properties/@";
import type {
	IProperties,
	Pitch,
	Positional,
	Sustain as T_Sustain,
	Transpose as T_Transpose,
	Trill as T_Trill,
} from "#schema/@";
import type { Cover } from "#types/helpers/@";
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

type Modifier = Cover<IProperties, "division" | "level" | "position">;

export class Properties {
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

	transform(modifier: Modifier): this {
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

		if (modifier.sustain !== undefined) {
			if (is<Positional<T_Sustain.Value>>(modifier.sustain)) {
				this.sustain.transform({ value: modifier.sustain }, { beat });
			} else {
				this.sustain.transform(modifier.sustain, { beat });
			}
		}

		if (modifier.transpose !== undefined) {
			if (is<Positional<T_Transpose.Value>>(modifier.transpose)) {
				this.transpose.transform({ value: modifier.transpose });
			} else {
				this.transpose.transform(modifier.transpose);
			}
		}

		return this;
	}

	fork(modifier: Modifier): Properties {
		const forked = new Properties();

		forked.beat = this.beat.fork(modifier.beat);
		forked.delay = this.delay.fork(modifier.delay);
		forked.time = this.time.fork(modifier.time);
		forked.trill = this.trill.fork(modifier.trill);
		forked.instrument = this.instrument.fork(modifier.instrument);

		if (is<Positional<T_Transpose.Value>>(modifier.transpose)) {
			forked.transpose = this.transpose.fork({ value: modifier.transpose });
		} else {
			forked.transpose = this.transpose.fork(modifier.transpose);
		}

		const beat = forked.beat.resolve();

		forked.dynamic = this.dynamic.fork(modifier.dynamic, { beat });

		if (is<Positional<T_Sustain.Value>>(modifier.sustain)) {
			forked.sustain = this.sustain.fork({ value: modifier.sustain }, { beat });
		} else {
			forked.sustain = this.sustain.fork(modifier.sustain, { beat });
		}

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

	resolveTrill(noteDuration: number) {
		const beat = this.beat.resolve();
		return this.trill.resolve({ noteDuration, beat });
	}

	resolvePhrasing(noteDuration: number) {
		const sustain = this.sustain.resolve({ noteDuration });
		const position = this.position.resolve({ noteDuration, sustain });
		const dynamic = this.dynamic.resolve({ noteDuration, sustain });
		return { sustain, position, dynamic };
	}

	resolveInstrument(args: {
		pitch: Pitch;
		trillValue: T_Trill.Value | undefined;
	}) {
		const transpose = this.transpose.resolve();
		return this.instrument.resolve({ ...args, ...transpose });
	}
}
