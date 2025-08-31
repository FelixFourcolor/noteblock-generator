import { times } from "lodash";
import type { SongResolution } from "#lib/resolver/@";
import { BoundTracker } from "./bound-tracker.js";
import { ErrorTracker } from "./error-tracker.js";
import { processSong } from "./song-processor.js";
import type { SongLayout } from "./types.js";

export async function assemble(song: SongResolution): Promise<SongLayout> {
	const errorTracker = new ErrorTracker();
	const boundTracker = new BoundTracker();

	const rawSlices = await Array.fromAsync(
		processSong({ song, errorTracker, boundTracker }),
	);

	const error = errorTracker.validate();
	if (error) {
		throw error;
	}

	const { minLevel, height } = boundTracker;
	const slices = rawSlices.map(({ delay, levelMap }) => ({
		delay,
		levels: times(height, (i) => levelMap[minLevel + i]),
	}));
	return {
		width: song.width,
		type: song.type,
		height,
		slices,
	};
}
