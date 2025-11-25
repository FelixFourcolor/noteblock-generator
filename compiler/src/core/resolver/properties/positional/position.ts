import { zipWith } from "lodash";
import { assert, is } from "typia";
import { splitVariableValue } from "#core/resolver/duration.js";
import type {
	Delete,
	Positional,
	Reset,
	Division as T_Division,
	Level as T_Level,
	Position as T_Position,
} from "#schema/@";
import { multiMap, type OneOrMany } from "../multi.js";
import type { ResolveType } from "../properties.js";
import { Division } from "./division.js";
import { Level } from "./level.js";
import type { Sustain } from "./sustain.js";

export class Position {
	readonly level: InstanceType<typeof Level>;
	readonly division: InstanceType<typeof Division>;

	static default(duration: {
		noteDuration: number;
		sustain: number | undefined;
	}) {
		return combine({
			level: Level.default(duration),
			division: Division.default(duration),
			...duration,
		});
	}

	constructor(args = { level: new Level(), division: new Division() }) {
		this.level = args.level;
		this.division = args.division;
	}

	transform(
		modifier: Positional<T_Level | T_Position> | undefined,
		args: { beat: number },
	) {
		const { level, division } = positionalSplit(
			assert<Positional<T_Position> | undefined>(modifier),
		);
		this.level.transform(level, args);
		this.division.transform(division, args);
		return this;
	}

	fork(
		modifier: Positional<T_Level | T_Position> | undefined,
		args: { beat: number },
	) {
		const { level, division } = positionalSplit(
			// T_level extends T_Position, but TS can't infer that
			modifier as Positional<T_Position> | undefined,
		);
		return new Position({
			level: this.level.fork(level, args),
			division: this.division.fork(division, args),
		});
	}

	resolve(duration: { noteDuration: number; sustain: OneOrMany<number> }) {
		return multiMap(combine, {
			level: this.level.resolve(duration),
			division: this.division.resolve(duration),
			...duration,
		});
	}
}

function combine({
	noteDuration,
	sustain,
	level = Level.default({ noteDuration, sustain }),
	division = Division.default({ noteDuration, sustain }),
}: {
	noteDuration: number;
	sustain: ResolveType<typeof Sustain>;
	level: ResolveType<typeof Level>;
	division: ResolveType<typeof Division>;
}) {
	return zipWith(level, division, (level, division) => ({ level, division }));
}

function positionalSplit(modifier: Positional<T_Position> | undefined) {
	let result: unknown;

	if (is<T_Position | Reset | undefined>(modifier)) {
		result = split(modifier);
	} else {
		const modifiers = modifier.map(split);
		result = {
			level: modifiers.map(({ level }) => level),
			division: modifiers.map(({ division }) => division),
		};
	}

	return result as {
		level: Positional<T_Level> | undefined;
		division: Positional<T_Division> | undefined;
	};
}

function split(modifier: T_Position | Reset | Delete | null | undefined) {
	if (is<Reset | Delete | null | undefined>(modifier)) {
		return { level: modifier, division: modifier };
	}
	return is<T_Position.uniform>(modifier)
		? uniformSplit(modifier)
		: variableSplit(modifier);
}

function uniformSplit(modifier: T_Position.uniform): {
	level: T_Level.uniform | undefined;
	division: T_Division.uniform | undefined;
} {
	if (typeof modifier === "number") {
		return { level: modifier, division: undefined };
	}

	const levelRegex = /([+-]?\d+)/;
	const levelMatch = modifier.match(levelRegex);
	const divisionString = (
		levelMatch ? modifier.replace(levelMatch[0], "") : modifier
	).trim();

	const level = levelMatch ? assert<T_Level.uniform>(levelMatch[0]) : undefined;
	const division = divisionString
		? assert<T_Division.uniform>(divisionString)
		: undefined;
	return { level, division };
}

function variableSplit(modifier: T_Position.variable): {
	level: T_Level.variable | undefined;
	division: T_Division.variable | undefined;
} {
	const parts = splitVariableValue(modifier).map(({ value, duration }) => {
		if (value === "~") {
			return { level: undefined, division: undefined, duration };
		}
		const { level, division } = uniformSplit(assert<T_Position.uniform>(value));
		return { level, division, duration };
	});
	const level = parts.some(({ level }) => level)
		? parts
				.map(({ level, duration }) => {
					if (!duration) {
						return level ?? "~";
					}
					return `${level ?? "~"}:${duration}`;
				})
				.join(";")
		: undefined;
	const division = parts.some(({ division }) => division)
		? parts
				.map(({ division, duration }) => {
					if (!duration) {
						return division ?? "~";
					}
					return `${division ?? "~"}:${duration}`;
				})
				.join(";")
		: undefined;
	return {
		level: assert<T_Level.variable | undefined>(level),
		division: assert<T_Division.variable | undefined>(division),
	};
}
