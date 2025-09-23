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
	Beat as T_Beat,
	Delay as T_Delay,
	Time as T_Time,
	Transpose as T_Transpose,
	Trill as T_Trill,
} from "#types/schema/@";
import type { ResolvedType } from "./positional.js";

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

		const beat = this.beat.resolve();

		this.level.transform(modifier.level, { beat });
		this.division.transform(modifier.division, { beat });
		this.position.transform(modifier.position, { beat });
		this.dynamic.transform(modifier.dynamic, { beat });
		this.sustain.transform(modifier.sustain, { beat });
		this.instrument.transform(modifier.instrument);
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

		if (modifier.position !== undefined) {
			forked.position = this.position.fork(modifier.position, { beat });
		} else {
			forked.position = new Position({
				level: this.level.fork(modifier.level, { beat }),
				division: this.division.fork(modifier.division, { beat }),
			});
		}
		forked.dynamic = this.dynamic.fork(modifier.dynamic, { beat });
		forked.sustain = this.sustain.fork(modifier.sustain, { beat });

		return forked;
	}

	resolve(_?: Record<any, never>): {
		beat: T_Beat;
		delay: T_Delay;
		time: T_Time;
		trill: T_Trill;
	};

	// @ts-expect-error (no idea what this error is, but it works at runtime)
	resolve(_: { noteDuration: number }): {
		position: ReturnType<Position["resolve"]>;
		sustain: ResolvedType<typeof Sustain>;
		dynamic: ResolvedType<typeof Dynamic>;
	};

	resolve(_: { pitch: Pitch; trill: T_Trill.Value | undefined }): {
		instrument: ResolvedType<typeof Instrument>;
	};

	resolve(_: {
		pitch: Pitch;
		trill: T_Trill.Value | undefined;
		noteDuration: number;
	}): {
		beat: T_Beat;
		delay: T_Delay;
		time: T_Time;
		trill: T_Trill;
		instrument: ResolvedType<typeof Instrument>;
		position: ReturnType<Position["resolve"]>;
		sustain: ResolvedType<typeof Sustain>;
		dynamic: ResolvedType<typeof Dynamic>;
	};

	resolve({
		pitch,
		trill,
		noteDuration,
	}: {
		pitch?: Pitch;
		trill?: T_Trill.Value | undefined;
		noteDuration?: number;
	} = {}) {
		const instrument = pitch
			? this.instrument.resolve({
					pitch,
					trill,
					...this.transpose.resolve(),
				})
			: undefined;
		const sustain = noteDuration
			? this.sustain.resolve({ noteDuration })
			: undefined;
		const position = noteDuration
			? this.position.resolve({ noteDuration, sustainDuration: sustain })
			: undefined;
		const dynamic = noteDuration
			? this.dynamic.resolve({ noteDuration, sustainDuration: sustain })
			: undefined;

		return {
			beat: this.beat.resolve(),
			delay: this.delay.resolve(),
			time: this.time.resolve(),
			trill: this.trill.resolve(),
			instrument,
			position,
			sustain,
			dynamic,
		};
	}
}
