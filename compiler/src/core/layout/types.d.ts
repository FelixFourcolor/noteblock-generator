import type { NoteBlock } from "@/core/resolver";
import type { Delay, TPosition } from "@/types/schema";

export type NoteCluster = readonly NoteBlock[];

export type LevelEntry<T extends TPosition> = T extends "single"
	? NoteCluster
	: readonly [NoteCluster, NoteCluster];

export type LevelMap<T extends TPosition = TPosition> = Record<
	number,
	LevelEntry<T>
>;

export type Slice<T extends TPosition = TPosition> = {
	delay: Delay;
	levels: ReadonlyArray<undefined | LevelEntry<T>>;
};

export type SongLayout<T extends TPosition = TPosition> = {
	type: T;
	height: number;
	width: number;
	slices: ReadonlyArray<Slice<T>>;
};
