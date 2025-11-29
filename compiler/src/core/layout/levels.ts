import { groupBy, mapValues } from "lodash";
import { match } from "ts-pattern";
import type { NoteEvent } from "#core/resolver/@";
import type { TPosition } from "#schema/@";
import type { ErrorTracker } from "./errors.js";
import { validateClusterSize } from "./errors.js";
import type { LevelEntry, LevelMap } from "./types.js";

export function mapLevels(
	notes: NoteEvent[],
	type: TPosition,
	{ registerError }: Pick<ErrorTracker, "registerError">,
): LevelMap {
	if (notes.length === 0) {
		return {};
	}

	// Already validated consistency, so just take the first's
	const measure = notes[0]!.measure;
	const onError = (error: string) => {
		registerError(error, measure);
	};

	return match(type)
		.with("single", () => mapSingle(notes, onError))
		.with("double", () => mapDouble(notes, onError))
		.exhaustive();
}

function mapSingle(
	notes: NoteEvent[],
	onError: (error: string) => void,
): LevelMap<"single"> {
	// For single builds, L and R are be duplicate, so just take the L
	const singleNotes = notes.filter((note) => note.division === "L");
	const levelGroups = groupBy(singleNotes, (note) => note.level);

	validateClusterSize(levelGroups, ([level, { voices, size }]) => {
		onError(`${voices.join(", ")}: Overflow @${level}=${size}`);
	});

	return mapValues(
		levelGroups,
		(notes): LevelEntry<"single"> => notes.map((note) => note.noteblock),
	);
}

function mapDouble(
	notes: NoteEvent[],
	onError: (error: string) => void,
): LevelMap<"double"> {
	const levelGroups = groupBy(notes, (note) => note.level);
	const positionGroups = mapValues(levelGroups, (notes) =>
		groupBy(notes, ({ division }) => division),
	);

	for (const [level, divisionGroups] of Object.entries(positionGroups)) {
		validateClusterSize(divisionGroups, ([division, { voices, size }]) => {
			onError(`${voices.join(", ")}: Overflow @${division}${level}=${size}`);
		});
	}

	return mapValues(
		positionGroups,
		({ L, R }): LevelEntry<"double"> => [
			L?.map((note) => note.noteblock) ?? [],
			R?.map((note) => note.noteblock) ?? [],
		],
	);
}
