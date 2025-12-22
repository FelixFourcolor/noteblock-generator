import { groupBy, mapValues } from "lodash";
import { match } from "ts-pattern";
import type { NoteBlock, NoteEvent } from "@/core/resolver";
import type { TPosition } from "@/types/schema";
import type { ErrorTracker } from "./tracker/errors";
import type { LevelMap } from "./types";
import { validateCluster } from "./validator/cluster-size";

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
	// For single builds, L and R are duplicate, so just take the L
	// TODO: optimize the data structure to not have duplicates in the first place
	const singleNotes = notes.filter((note) => note.division === "L");
	const levelGroups = groupBy(singleNotes, (note) => note.level);

	validateCluster(levelGroups, ([level, { voices, size }]) => {
		onError(`${voices.join(", ")}: Overflow @${level}=${size}`);
	});

	return mapValues(levelGroups, (notes) =>
		notes.map((note) => note.noteblock).toSorted(sorter),
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
		validateCluster(divisionGroups, ([division, { voices, size }]) => {
			onError(`${voices.join(", ")}: Overflow @${division}${level}=${size}`);
		});
	}

	return mapValues(
		positionGroups,
		({ L, R }) =>
			[
				L?.map((note) => note.noteblock).toSorted(sorter) ?? [],
				R?.map((note) => note.noteblock).toSorted(sorter) ?? [],
			] as const,
	);
}

// Sort note cluster for stable test snapshots
// and (possibly) more efficient caching
function sorter(a: NoteBlock, b: NoteBlock) {
	return a.instrument.localeCompare(b.instrument) || a.note - b.note;
}
