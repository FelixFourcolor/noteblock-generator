import type { NoteBlock } from "#core/resolver/@";
import type { Delay, Name, SongModifier, TPosition } from "#types/schema/@";

type TEvent = keyof variants;
interface variants {
	note: { delay: Delay; noteblock: NoteBlock };
	rest: { delay: Delay; noteblock: undefined };
	error: { error: string };
}

export interface Measure {
	bar: number;
	tick: number;
}

export type TickEvent<T extends TEvent = TEvent> = variants[T];

export namespace TickEvent {
	export type Phrased<T extends TEvent = TEvent> = T extends "note"
		? TickEvent<T> & { level: number; division: "L" | "R" }
		: TickEvent<T>;
	export type Voiced<T extends TEvent = TEvent> = Phrased<T> & {
		voice: Name;
		measure: Measure;
	};
}

export type Tick<T extends TEvent = TEvent> = TickEvent.Voiced<T>[];

export type Resolution = {
	width: number;
	type: TPosition;
	ticks: AsyncGenerator<Tick>;
};

export type SongContext = { songModifier: SongModifier; cwd: string };
export type VoiceContext = SongContext & { index: number };
