import type { DistributiveOmit } from "@/types/helpers";
import type { IProperties, TPosition } from ".";

export type PresetId = `$${string}`;

export type Preset<T extends TPosition = TPosition> =
	| DistributiveOmit<IProperties<T>, "presets">
	| PresetId;

export type PresetStore<T extends TPosition = TPosition> = Record<
	/**
	 * Using `string` instead of `PresetId` because
	 *   - Key name cannot be enforced at schema-level (no in-editor error)
	 *   - When key is not prefixed, lookup will fail anyway
	 *   - Lookup error messages look prettier than schema validation errors
	 */
	string,
	Preset<T>
>;

export type PresetSetter<T = TPosition> = {
	presets?: PresetStore<T extends TPosition ? T : TPosition>;
};

export type PresetGetter = { preset?: PresetId };

export type IPreset<T = TPosition> = PresetGetter &
	PresetSetter<T extends TPosition ? T : TPosition>;
