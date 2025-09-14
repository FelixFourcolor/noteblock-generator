import { type Type, type } from "arktype";
import type { TPosition } from "../properties/positional/position.js";
import { IProperties } from "../properties/properties.js";
import { Deferred } from "./deferred.js";
import { Notes, Voice } from "./voice.js";

function VoiceGroup<
	T extends TPosition,
	TValidate extends "lazy" | "eager" = "lazy",
>(t?: T, validate?: TValidate) {
	return Deferred(Voice(t, validate)).array().atLeastLength(2) satisfies Type<
		VoiceGroup<T, TValidate>
	>;
}

function VoiceEntry<
	T extends TPosition,
	TValidate extends "lazy" | "eager" = "lazy",
>(t?: T, validate?: TValidate) {
	return type.or(
		type.null,
		Deferred(Voice(t, validate)) as any,
		VoiceGroup(t, validate),
	) as unknown as Type<VoiceEntry<T, TValidate>>;
}

export function Voices<
	T extends TPosition = TPosition,
	TValidate extends "lazy" | "eager" = "lazy",
>(t?: T, validate?: TValidate) {
	return VoiceEntry(t, validate).array().atLeastLength(1) satisfies Type<
		Voices<T, TValidate>
	>;
}

export function Song<
	T extends TPosition,
	TValidate extends "lazy" | "eager" = "lazy",
>(t?: T, validate?: TValidate) {
	return type.or(
		IProperties(t).and({ voices: Voices(t, validate) }) as any,
		Voice(t, validate) as any,
		Notes(t, validate),
	) as unknown as Type<Song<T, TValidate>>;
}

type VoiceGroup<
	T extends TPosition,
	TValidate extends "lazy" | "eager" = "lazy",
> = Deferred<Voice<T, TValidate>>[];

export type VoiceEntry<
	T extends TPosition,
	TValidate extends "lazy" | "eager" = "lazy",
> =
	| null //
	| VoiceGroup<T, TValidate>[number]
	| VoiceGroup<T, TValidate>;

export type Voices<
	T extends TPosition = TPosition,
	TValidate extends "lazy" | "eager" = "lazy",
> = VoiceEntry<T, TValidate>[];

export type Song<
	T extends TPosition = TPosition,
	TValidate extends "lazy" | "eager" = "lazy",
> =
	| ({ voices: Voices<T, TValidate> } & IProperties<T>)
	| Voice<T, TValidate>
	| Notes<TPosition, TValidate>;

