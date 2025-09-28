import { Properties } from "#core/resolver/properties/@";
import type { IGlobalProperties, IPositionalProperties } from "#types/schema/@";
import type { DistributiveOmit } from "#types/utils/@";
import { Measure, type MeasureModifier } from "./measure.js";

type TransformModifier =
	| DistributiveOmit<MeasureModifier, "time">
	| IPositionalProperties;

class ContextClass extends Properties {
	private _measure = new Measure();

	get bar() {
		return this._measure.bar;
	}
	get tick() {
		return this._measure.tick;
	}
	get measure() {
		return { bar: this.bar, tick: this.tick };
	}
	get voice() {
		return this.name.resolve();
	}

	override transform(modifier: TransformModifier) {
		if ("bar" in modifier || "noteDuration" in modifier) {
			const time = this.time.resolve();
			this._measure.transform({ ...modifier, time });
		} else {
			super.transform(modifier);
		}
		return this;
	}

	override fork(modifier: IGlobalProperties = {}) {
		const forkedContext = new ContextClass();
		const forkedProperties = super.fork(modifier);
		forkedContext._measure = this._measure;
		Object.assign(forkedContext, forkedProperties);
		return forkedContext;
	}
}

export type MutableContext = ContextClass;
export type Context = Omit<MutableContext, "transform">;

export const Context: new (
	...args: ConstructorParameters<typeof ContextClass>
) => MutableContext = ContextClass;
