import { createIs, is } from "typia";
import type { Cover } from "@/types/helpers";
import type {
	IProperties,
	Pitch,
	Positional,
	Preset,
	PresetId,
	PresetStore,
	Sustain as T_Sustain,
	Transpose as T_Transpose,
	Trill as T_Trill,
} from "@/types/schema";
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
} from ".";
import type { OneOrMany } from "./multi";
import type { PositionalClass } from "./positional";
import type { StaticClass } from "./static";

export type ResolveType<T> =
	T extends StaticClass<infer U>
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

export type PropertiesModifier =
	| Cover<IProperties, "division" | "level" | "position">
	| PresetId;

export class Properties {
	constructor(
		private presets: PresetStore = {},
		protected beat = new Beat(),
		protected delay = new Delay(),
		protected time = new Time(),
		protected trill = new Trill(),
		protected dynamic = new Dynamic(),
		protected sustain = new Sustain(),
		protected transpose = new Transpose(),
		protected instrument = new Instrument(),
		protected position = new Position(),
	) {}

	get level() {
		return this.position.level;
	}
	get division() {
		return this.position.division;
	}

	private resolvePreset(id: PresetId, visited: Set<PresetId>): Preset {
		if (visited.has(id)) {
			throw new PresetCircularReference(id);
		}
		visited.add(id);

		const lookup = this.presets[id];
		if (!lookup) {
			throw new PresetNotFound(id);
		}

		if (isPresetId(lookup)) {
			return this.resolvePreset(lookup, visited);
		}
		return lookup;
	}

	transform(modifier: PropertiesModifier): this {
		return this._transform(modifier, new Set());
	}
	private _transform(
		modifier: PropertiesModifier,
		visited: Set<PresetId>,
	): this {
		if (isPresetId(modifier)) {
			return this._transform(this.resolvePreset(modifier, visited), visited);
		}

		const { presets, preset, ...properties } = modifier;
		this.presets = { ...this.presets, ...presets };
		if (preset) {
			this._transform(this.resolvePreset(preset, visited), visited);
		}

		const {
			beat: beatModifier,
			delay,
			time,
			trill,
			instrument,
			level,
			division,
			position,
			dynamic,
			sustain,
			transpose,
			...__unused
		} = properties;
		__unused satisfies Record<string, never>;

		this.beat.transform(beatModifier);
		this.delay.transform(delay);
		this.time.transform(time);
		this.trill.transform(trill);
		this.instrument.transform(instrument);

		const beat = this.beat.resolve();

		this.level.transform(level, { beat });
		this.division.transform(division, { beat });
		this.position.transform(position, { beat });
		this.dynamic.transform(dynamic, { beat });

		if (sustain !== undefined) {
			if (is<Positional<T_Sustain.Value>>(sustain)) {
				this.sustain.transform({ value: sustain }, { beat });
			} else {
				this.sustain.transform(sustain, { beat });
			}
		}

		if (transpose !== undefined) {
			if (is<Positional<T_Transpose.Value>>(transpose)) {
				this.transpose.transform({ value: transpose });
			} else {
				this.transpose.transform(transpose);
			}
		}

		return this;
	}

	fork(modifier: PropertiesModifier): Properties {
		return this._fork(modifier, new Set());
	}
	private _fork(
		modifier: PropertiesModifier,
		visited: Set<PresetId>,
	): Properties {
		if (isPresetId(modifier)) {
			return this._fork(this.resolvePreset(modifier, visited), visited);
		}

		const { preset, presets, ...properties } = modifier;
		const forked = new Properties(
			{ ...this.presets, ...presets },
			this.beat,
			this.delay,
			this.time,
			this.trill,
			this.dynamic,
			this.sustain,
			this.transpose,
			this.instrument,
			this.position,
		);
		if (preset) {
			return forked
				._fork(forked.resolvePreset(preset, visited), visited)
				._fork(properties, visited);
		}

		const {
			beat: beatModifier,
			delay,
			time,
			trill,
			instrument,
			level: levelModifier,
			division: divisionModifier,
			position,
			dynamic,
			sustain,
			transpose,
			..._unused
		} = properties;
		_unused satisfies Record<string, never>;

		forked.beat = this.beat.fork(beatModifier);
		forked.delay = this.delay.fork(delay);
		forked.time = this.time.fork(time);
		forked.trill = this.trill.fork(trill);
		forked.instrument = this.instrument.fork(instrument);

		if (is<Positional<T_Transpose.Value>>(transpose)) {
			forked.transpose = this.transpose.fork({ value: transpose });
		} else {
			forked.transpose = this.transpose.fork(transpose);
		}

		const beat = forked.beat.resolve();

		forked.dynamic = this.dynamic.fork(dynamic, { beat });

		if (is<Positional<T_Sustain.Value>>(sustain)) {
			forked.sustain = this.sustain.fork({ value: sustain }, { beat });
		} else {
			forked.sustain = this.sustain.fork(sustain, { beat });
		}

		if (position !== undefined) {
			forked.position = this.position.fork(position, { beat });
		} else {
			const level = this.level.fork(levelModifier, { beat });
			const division = this.division.fork(divisionModifier, { beat });
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

export class PresetError extends Error {}
class PresetNotFound extends PresetError {
	constructor(presetId: PresetId) {
		super(`Preset '${presetId}' not found`);
	}
}
class PresetCircularReference extends PresetError {
	constructor(presetId: PresetId) {
		super(`Preset '${presetId}' has a circular reference`);
	}
}

const isPresetId = createIs<PresetId>();
