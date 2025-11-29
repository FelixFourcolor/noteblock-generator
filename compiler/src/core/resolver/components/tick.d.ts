import type { Delay } from "#schema/@";
import type { NoteBlock } from "../properties/index.js";
import type { IMeasure } from "./utils/measure.js";

type TEvent = keyof variants;
interface variants {
	note: { delay: Delay; noteblock: NoteBlock };
	rest: { delay: Delay; noteblock: undefined };
	error: { error: string };
}

export type TickEvent<T extends TEvent = TEvent> = variants[T];

export namespace TickEvent {
	export type Phrased<T extends TEvent = TEvent> = T extends "note"
		? TickEvent<T> & { level: number; division: "L" | "R" }
		: TickEvent<T>;
	export type Voiced<T extends TEvent = TEvent> = Phrased<T> & {
		voice: string;
		measure: IMeasure;
	};
}

export type Tick<T extends TEvent = TEvent> = TickEvent.Voiced<T>[];

export type NoteEvent = TickEvent.Voiced<"note">;
