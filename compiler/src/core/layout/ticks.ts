import { partition } from "lodash";
import { match, P } from "ts-pattern";
import type { Tick } from "#core/resolver/@";
import type { TPosition } from "#schema/@";
import { type ErrorTracker, validateConsistency } from "./errors.js";
import type { HeightTracker } from "./height.js";
import { mapLevels } from "./levels.js";
import type { LevelMap } from "./types.js";

export function* processTicks(
	ticks: Iterable<Tick>,
	type: TPosition,
	{ registerLevel }: Pick<HeightTracker, "registerLevel">,
	{ registerError }: Pick<ErrorTracker, "registerError">,
): Generator<{ delay: number; levelMap: LevelMap }> {
	let measure = { bar: 1, tick: 0 };

	for (const tick of ticks) {
		const [errors, events] = partition(tick, (event) => "error" in event);

		errors.forEach(({ voice, error, measure }) => {
			registerError(`${voice}: ${error}`, measure);
		});

		if (events.length === 0) {
			continue;
		}

		measure = match(validateConsistency(events, "measure"))
			.with({ value: P.select() }, (measure) => measure)
			.otherwise(({ error }) => {
				registerError(error, measure);
				return measure;
			});

		const delay = match(validateConsistency(events, "delay"))
			.with({ value: P.select() }, (delay) => delay)
			.otherwise(({ error }) => {
				registerError(error, measure);
				return 1;
			});

		const notes = events.filter((event) => event.noteblock != null);
		const levelMap = mapLevels(notes, type, { registerError });
		Object.keys(levelMap).map(Number).map(registerLevel);

		yield { delay, levelMap };
	}
}
