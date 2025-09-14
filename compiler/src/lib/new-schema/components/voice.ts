import { type Type, type } from "arktype";
import { BarLine } from "../note/barline.js";
import type { TPosition } from "../properties/positional/position.js";
import { IProperties } from "../properties/properties.js";
import { Deferred } from "./deferred.js";
import { Chord, Note } from "./note.js";

export function FutureModifier<T extends TPosition>(t?: T) {
	return IProperties(t as TPosition | undefined).omit("width", "name") as Type<
		FutureModifier<T>
	>;
}

export function Notes<
	T extends TPosition,
	TValidate extends "lazy" | "eager" = "lazy",
>(t?: T, validate?: TValidate) {
	const T = t as TPosition | undefined;
	let noteItem = type.or(BarLine, Note(T), Chord(T), FutureModifier(T));
	if (validate !== "eager") {
		noteItem = noteItem.or("unknown") as any;
	}
	return noteItem.array().atLeastLength(1) as Type<Notes<T, TValidate>>;
}

export function VoiceModifier<T extends TPosition>(t?: T) {
	return IProperties(t as TPosition | undefined).omit("width") as Type<
		VoiceModifier<T>
	>;
}

export function Voice<
	T extends TPosition,
	TValidate extends "lazy" | "eager" = "lazy",
>(t?: T, validate?: TValidate) {
	return VoiceModifier(t).and({
		notes: Deferred(Notes(t, validate)),
	}) as unknown as Type<Voice<T, TValidate>>;
}

export type FutureModifier<T extends TPosition> = Omit<
	IProperties<T>,
	"name" | "width"
>;

export type Notes<
	T extends TPosition,
	TValidate extends "lazy" | "eager" = "lazy",
> = (
	| BarLine
	| Note<T>
	| Chord<T>
	| FutureModifier<T>
	| (TValidate extends "lazy" ? unknown : never)
)[];

export type VoiceModifier<T extends TPosition> = Omit<IProperties<T>, "width">;

export type Voice<
	T extends TPosition,
	TValidate extends "lazy" | "eager" = "lazy",
> = VoiceModifier<T> & { notes: Deferred<Notes<T, TValidate>> };
