import type { NoteBlock } from "#core/resolver/@";
import type { Delay, TPosition } from "#schema/@";

export type NoteCluster = NoteBlock[];

export type LevelEntry<T extends TPosition> = T extends "single"
	? NoteCluster
	: [NoteCluster, NoteCluster];

export type LevelMap<T extends TPosition = TPosition> = Record<
	number,
	LevelEntry<T>
>;

export type Slice<T extends TPosition = TPosition> = {
	delay: Delay;
	levels: (LevelMap<T>[number] | undefined)[];
};

export type SongLayout<T extends TPosition = TPosition> = {
	type: T;
	height: number;
	width: number;
	slices: Slice<T>[];
};
