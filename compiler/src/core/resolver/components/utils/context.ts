import { isEmpty } from "lodash";
import { Properties } from "@/core/resolver/properties";
import type { IProperties } from "@/types/schema";
import { type IMeasure, Measure } from "./measure";

type TransformModifier = IMeasure | { noteDuration: number } | IProperties;

class ContextClass extends Properties {
	private _measure = new Measure();
	get measure() {
		const { tick, bar } = this._measure;
		return { tick, bar };
	}
	get bar() {
		return this._measure.bar;
	}
	get tick() {
		return this._measure.tick;
	}

	constructor(public voice: string) {
		super();
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

	override fork(modifier: IProperties = {}) {
		if (isEmpty(modifier)) {
			return this;
		}

		const forkedContext = new ContextClass(this.voice);
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
