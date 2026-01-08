import {
	Properties,
	type PropertiesModifier,
} from "@/core/resolver/properties";
import { type IMeasure, Measure } from "./measure";

type TransformModifier =
	| PropertiesModifier
	| IMeasure
	| { noteDuration: number };

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
		if (
			typeof modifier === "object" &&
			("bar" in modifier || "noteDuration" in modifier)
		) {
			const time = this.time.resolve();
			this._measure.transform({ ...modifier, time });
			return this;
		}
		return super.transform(modifier);
	}

	override fork(modifier: PropertiesModifier) {
		const forkedContext = new ContextClass(this.voice);
		const forkedProperties = super.fork(modifier);
		forkedContext._measure = new Measure(this._measure);
		return safeObjectAssign(forkedContext, forkedProperties);
	}
}

const safeObjectAssign = <T extends S, S extends object>(
	target: T,
	source: S,
): T => Object.assign(target, source);

export type MutableContext = ContextClass;
export type Context = Omit<MutableContext, "transform">;

export const Context: new (
	...args: ConstructorParameters<typeof ContextClass>
) => MutableContext = ContextClass;
