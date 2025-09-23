import { groupBy, mapValues } from "lodash";
import { match } from "ts-pattern";
import type { Measure } from "#core/resolver/@";
import type { TPosition } from "#types/schema/@";
import type { ErrorTracker } from "./error-tracker.js";
import type { LevelEntry, LevelMap, NoteEvent } from "./types.js";
import { checkOverflow } from "./validation.js";

type MapperContext = {
	notes: NoteEvent[];
	type: TPosition;
	errorTracker: ErrorTracker;
};

export abstract class LevelMapper<T extends TPosition> {
	static map(ctx: MapperContext): LevelMap {
		return match(ctx)
			.with({ notes: [] }, () => ({}))
			.with({ type: "single" }, () => new SingleMapper(ctx).getLevelMap())
			.with({ type: "double" }, () => new DoubleMapper(ctx).getLevelMap())
			.exhaustive();
	}

	abstract getLevelMap(): LevelMap<T>;

	protected notes: NoteEvent[];
	private errorTracker: ErrorTracker;
	private measure: Measure;

	constructor({ notes, errorTracker }: MapperContext) {
		this.notes = notes;
		this.errorTracker = errorTracker;
		// We already validated measure consistency, so the first index can represent all
		this.measure = notes[0]!.measure;
	}

	protected registerError(error: string) {
		this.errorTracker.registerError({ measure: this.measure, error });
	}
}
class SingleMapper extends LevelMapper<"single"> {
	override getLevelMap() {
		// For single builds, L and R are be duplicate, so just take the L
		const singleNotes = this.notes.filter(({ division }) => division === "L");
		const levelGroups = groupBy(singleNotes, ({ level }) => level);

		checkOverflow({
			noteGroups: levelGroups,
			onError: ({ groupKey: level, voices, count }) => {
				this.registerError(`${voices.join(", ")}: Overflow @${level}=${count}`);
			},
		});

		return mapValues(levelGroups, (notes) =>
			notes.map(({ noteblock }) => noteblock),
		);
	}
}

class DoubleMapper extends LevelMapper<"double"> {
	override getLevelMap() {
		const levelGroups = groupBy(this.notes, ({ level }) => level);
		const positionGroups = mapValues(levelGroups, (notes) =>
			groupBy(notes, ({ division }) => division),
		);

		for (const [level, divisionGroups] of Object.entries(positionGroups)) {
			checkOverflow({
				noteGroups: divisionGroups,
				onError: ({ groupKey: division, voices, count }) => {
					this.registerError(
						`${voices.join(", ")}: Overflow @${division}${level}=${count}`,
					);
				},
			});
		}

		return mapValues(
			positionGroups,
			({ L, R }): LevelEntry<"double"> => [
				L?.map(({ noteblock }) => noteblock) ?? [],
				R?.map(({ noteblock }) => noteblock) ?? [],
			],
		);
	}
}
