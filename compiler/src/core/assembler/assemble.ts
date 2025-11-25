import { times } from "lodash";
import { UserError } from "#cli/error.js";
import type { SongResolution } from "#core/resolver/@";
import { BoundsTracker } from "./bounds-tracker.js";
import { ErrorTracker } from "./error-tracker.js";
import { processSong } from "./song-processor.js";
import type { SongLayout } from "./types.js";

export function assemble(song: SongResolution): SongLayout {
	const errorTracker = new ErrorTracker();
	const boundTracker = new BoundsTracker();

	const sliceGenerator = processSong(song, boundTracker, errorTracker);
	const rawSlices = Array.from(sliceGenerator);
	if (rawSlices.length === 0) {
		throw new UserError("Song is empty.");
	}

	const error = errorTracker.validate();
	if (error) {
		throw error;
	}

	const { minLevel, height } = boundTracker;
	const slices = rawSlices.map(({ delay, levelMap }) => ({
		delay,
		levels: times(height, (i) => levelMap[minLevel + i]),
	}));

	const { width, type } = song;
	return { width, type, height, slices };
}
