import { partition } from "lodash";
import { match, P } from "ts-pattern";
import type { SongResolution } from "#core/resolver/@";
import type { BoundsTracker } from "./bounds-tracker.js";
import type { ErrorTracker } from "./error-tracker.js";
import { LevelMapper } from "./level-mapper.js";
import type { LevelMap } from "./types.js";
import { validateConsistency } from "./validation.js";

type SongProcessingContext = {
	song: SongResolution;
	boundTracker: BoundsTracker;
	errorTracker: ErrorTracker;
};

export async function* processSong(
	ctx: SongProcessingContext,
): AsyncGenerator<{ delay: number; levelMap: LevelMap }> {
	const { song, boundTracker, errorTracker } = ctx;
	const { type, ticks } = song;
	const { registerLevel } = boundTracker;
	const { registerError } = errorTracker;

	let measure = { bar: 1, tick: 0 };

	for await (const tick of ticks) {
		const [errors, events] = partition(tick, (event) => "error" in event);

		for (const { measure, voice, error } of errors) {
			registerError({ measure, error: `${voice}: ${error}` });
		}

		if (events.length === 0) {
			continue;
		}

		measure = match(validateConsistency(events, "measure"))
			.with({ value: P.select() }, (measure) => measure)
			.otherwise(({ error }) => {
				registerError({ measure, error });
				return measure;
			});

		const delay = match(validateConsistency(events, "delay"))
			.with({ value: P.select() }, (delay) => delay)
			.otherwise(({ error }) => {
				registerError({ measure, error });
				return 1;
			});

		const notes = events.filter((event) => event.noteblock != null);
		const levelMap = LevelMapper.map({ notes, type, errorTracker });
		Object.keys(levelMap).map(Number).map(registerLevel);
		yield { delay, levelMap };
	}
}
