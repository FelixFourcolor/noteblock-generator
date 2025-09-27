import { match, P } from "ts-pattern";
import { is } from "typia";
import {
	Beat,
	Delay,
	Dynamic,
	Instrument,
	isMulti,
	multi,
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
	Transpose as T_Transpose,
	Trill as T_Trill,
} from "#types/schema/@";

export class Properties {
	beat = new Beat();
	delay = new Delay();
	time = new Time();
	trill = new Trill();
	dynamic = new Dynamic();
	sustain = new Sustain();
	transpose = new Transpose();
	instrument = new Instrument();

	position = new Position();
	get level() {
		return this.position.level;
	}
	get division() {
		return this.position.division;
	}

	transform(modifier: Partial<Omit<IProperties, "name" | "width">>): this {
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

	fork(modifier: Partial<Omit<IProperties, "name" | "width">>): Properties {
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

	resolveTrill({ noteDuration }: { noteDuration: number }) {
		return this.trill.resolve({ noteDuration, beat: this.beat.resolve() });
	}

	resolvePhrasing({ noteDuration }: { noteDuration: number }) {
		const sustainDuration = this.sustain.resolve({ noteDuration });
		const position = this.position.resolve({ noteDuration, sustainDuration });
		const dynamic = this.dynamic.resolve({ noteDuration, sustainDuration });
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
		return match(this.instrument.resolve({ ...args, ...transpose }))
			.with(P.when(isMulti), (instruments) => ({
				mainBlock: multi(instruments.map(({ mainBlock }) => mainBlock)),
				trillBlock: multi(instruments.map(({ trillBlock }) => trillBlock)),
			}))
			.otherwise((instrument) => instrument);
	}
}
