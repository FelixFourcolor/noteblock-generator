import { Properties } from "#lib/resolver/properties/@";
import type { IProperties, Name } from "#lib/schema/types/@";
import type { AtMostOneOf } from "#lib/schema/types/utils/@";
import type { Measure } from "./voice.js";

class ContextClass extends Properties {
	readonly name: Name;

	measure: Measure;
	get bar() {
		return this.measure.bar;
	}
	get tick() {
		return this.measure.tick;
	}

	constructor(name: Name, measure: Measure = { bar: 1, tick: 1 }) {
		super();
		this.name = name;
		this.measure = { ...measure };
	}

	override transform({
		measure,
		noteDuration,
		...propsModifier
	}: AtMostOneOf<{ noteDuration: number; measure: Measure }> &
		Partial<Omit<IProperties, "name" | "width">>) {
		if (measure !== undefined) {
			this.measure = measure;
		} else if (noteDuration !== undefined) {
			let { bar, tick } = this.measure;
			const time = this.time.resolve();
			tick += noteDuration - 1;
			bar += Math.floor(tick / time);
			tick = 1 + (tick % time);
			this.measure = { bar, tick };
		}

		return super.transform(propsModifier);
	}

	override fork({
		name,
		measure,
		...propsModifier
	}: Partial<{ measure: Measure } & Omit<IProperties, "width">> = {}) {
		const forkedContext = new ContextClass(
			name ? `${this.name} / ${name}` : this.name,
			measure ?? this.measure,
		);
		const forkedProperties = super.fork(propsModifier);
		Object.assign(forkedContext, forkedProperties);
		return forkedContext;
	}
}

export type MutableContext = ContextClass;
export type Context = Omit<MutableContext, "transform">;

export const Context: new (name: Name) => MutableContext = ContextClass;
