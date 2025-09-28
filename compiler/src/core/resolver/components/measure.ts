import { match, P } from "ts-pattern";
import type { Time } from "#types/schema/@";
import type { Measure as T_Measure } from "./types.js";

export type MeasureModifier = T_Measure | { time: Time; noteDuration: number };

export class Measure implements T_Measure {
	private measure = { bar: 1, tick: 1 };

	get bar() {
		return this.measure.bar;
	}
	get tick() {
		return this.measure.tick;
	}

	transform(modifier: MeasureModifier) {
		this.measure = match(modifier)
			.with({ bar: P.nonNullable }, (measure) => measure)
			.with({ noteDuration: P.nonNullable }, ({ noteDuration, time }) => {
				let { bar, tick } = this.measure;
				tick += noteDuration - 1;
				bar += Math.floor(tick / time);
				tick = 1 + (tick % time);
				return { bar, tick };
			})
			.otherwise(() => this.measure);
	}

	resolve() {
		return this.measure;
	}
}
