import { times } from "lodash";
import { UserError } from "#cli/error.js";
import type { NoteBlock, SongResolution, Tick } from "#core/resolver/@";
import type { Delay, TPosition } from "#schema/@";
import { ErrorTracker } from "./errors.js";
import { HeightTracker } from "./height.js";
import { processTicks } from "./ticks.js";

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

export function calculateLayout({
	type,
	width,
	ticks,
}: SongResolution): SongLayout<typeof type> {
	const errorTracker = new ErrorTracker();
	const boundTracker = new HeightTracker();

	const levelMaps = Array.from(
		processTicks(ticks, type, boundTracker, errorTracker),
	);
	if (levelMaps.length === 0) {
		throw new UserError("Song is empty.");
	}
	const error = errorTracker.validate();
	if (error) {
		throw error;
	}

	const { minLevel, height } = boundTracker;
	const slices = levelMaps.map(({ delay, levelMap }) => ({
		delay,
		levels: times(height, (i) => levelMap[minLevel + i]),
	}));
	return { type, height, width, slices };
}
