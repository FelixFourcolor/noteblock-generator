import type { NoteBlock } from "#core/resolver/@";
import type { Delay, Name, SongModifier, TPosition } from "#types/schema/@";

type TEvent = keyof variants;
interface variants {
	note: { delay: Delay; noteblock: NoteBlock };
	rest: { delay: Delay; noteblock?: undefined };
	error: { error: string };
}

export type Measure = { bar: number; tick: number };

export type TickEvent<T extends TEvent = TEvent> = TickEvent.Raw<T>;
export type Tick<T extends TEvent = TEvent> = TickEvent.Voiced<T>[];

export namespace TickEvent {
	export type Raw<T extends TEvent = TEvent> = variants[T];
	export type Phrased<T extends TEvent = TEvent> = T extends "note"
		? Raw<T> & { level: number; division: "L" | "R" }
		: Raw<T>;
	export type Voiced<T extends TEvent = TEvent> = Phrased<T> & {
		voice: Name;
		measure: Measure;
	};
}

export type Resolution = { type: TPosition; ticks: AsyncGenerator<Tick> };
export type SongResolution = Resolution & { width: number };

export type SongContext = { songModifier: SongModifier; cwd: string };
export type VoiceContext = SongContext & { index: number };
