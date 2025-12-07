import { partition } from "lodash";
import { match, P } from "ts-pattern";
import type { Tick } from "@/core/resolver";
import type { TPosition } from "@/types/schema";
import { mapLevels } from "./level-mapper";
import type { ErrorTracker } from "./tracker/errors";
import type { HeightTracker } from "./tracker/height";
import type { LevelMap } from "./types";
import { validateConsistency } from "./validator/consistency";

export function* processTicks(
	ticks: Iterable<Tick>,
	type: TPosition,
	{ registerLevel }: Pick<HeightTracker, "registerLevel">,
	{ registerError }: Pick<ErrorTracker, "registerError">,
): Generator<{ delay: number; levelMap: LevelMap }> {
	let measure = { bar: 1, tick: 0 };
	let defaultDelay = 1;

	for (const tick of ticks) {
		const [errors, events] = partition(tick, (event) => "error" in event);

		errors.forEach(({ voice, error, measure }) => {
			registerError(`${voice}: ${error}`, measure);
		});

		if (events.length === 0) {
			continue;
		}

		measure = match(validateConsistency(events, "measure"))
			.with({ error: P.select() }, (error) => {
				registerError(error, measure);
				return measure;
			})
			.otherwise(({ value }) => value);

		const delay = match(validateConsistency(events, "delay"))
			.with({ error: P.select() }, (error) => {
				registerError(error, measure);
				return defaultDelay;
			})
			.otherwise(({ value, defaultValue }) => {
				defaultDelay = defaultValue;
				return value;
			});

		const notes = events.filter((event) => event.noteblock != null);
		const levelMap = mapLevels(notes, type, { registerError });
		Object.keys(levelMap).map(Number).map(registerLevel);

		yield { delay, levelMap };
	}
}
