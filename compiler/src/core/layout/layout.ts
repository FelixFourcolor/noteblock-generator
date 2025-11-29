import { times } from "lodash";
import { UserError } from "#cli/error.js";
import type { SongResolution } from "#core/resolver/@";
import { ErrorTracker } from "./errors.js";
import { HeightTracker } from "./height.js";
import { processTicks } from "./ticks.js";
import type { SongLayout } from "./types.js";

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

	const error = errorTracker.validate();
	if (error) {
		throw error;
	}

	const { minLevel, height } = boundTracker;
	if (levelMaps.length === 0 || height === 0) {
		throw new UserError("Song is empty.");
	}

	const slices = levelMaps.map(({ delay, levelMap }) => ({
		delay,
		levels: times(height, (i) => levelMap[minLevel + i]),
	}));
	return { type, height, width, slices };
}
