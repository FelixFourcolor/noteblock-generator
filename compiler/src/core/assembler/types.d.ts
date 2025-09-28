import type { NoteBlock, TickEvent } from "#core/resolver/@";
import type { Delay, TPosition } from "#schema/@";

export type NoteEvent = TickEvent.Voiced<"note">;

export type NoteCluster = NoteBlock[];

export type LevelEntry<T extends TPosition> = T extends "single"
	? NoteCluster
	: [NoteCluster, NoteCluster];

export type LevelMap<T extends TPosition = TPosition> = Record<
	number,
	LevelEntry<T>
>;

export type LevelArray<T extends TPosition> = (LevelEntry<T> | undefined)[];

export type Slice<T extends TPosition = TPosition> = {
	delay: Delay;
	levels: LevelArray<T>;
};

export type SongLayout<T extends TPosition = TPosition> = {
	width: number;
	height: number;
	type: T;
	slices: Slice<T>[];
};
