import { zipWith } from "lodash";
import { assert, is } from "typia";
import { splitVariableValue } from "#lib/resolver/duration.js";
import type {
	Delete,
	Positional,
	Reset,
	Division as T_Division,
	Level as T_Level,
	Position as T_Position,
} from "#lib/schema/types/@";
import { multiMap, type OneOrMany } from "../positional.js";
import { Division } from "./division.js";
import { Level } from "./level.js";

export class Position {
	readonly level: InstanceType<typeof Level>;
	readonly division: InstanceType<typeof Division>;

	static default(duration: {
		noteDuration: number;
		sustainDuration: number | undefined;
	}) {
		return combine({
			level: Level.default(duration),
			division: Division.default(duration),
			...duration,
		});
	}

	constructor({
		level = new Level(),
		division = new Division(),
	}: {
		level?: InstanceType<typeof Level>;
		division?: InstanceType<typeof Division>;
	} = {}) {
		this.level = level;
		this.division = division;
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
			assert<Positional<T_Position> | undefined>(modifier),
		);
		const forkedLevel = this.level.fork(level, args);
		const forkedDivision = this.division.fork(division, args);

		const ctor = this.constructor as new (_: {
			level: InstanceType<typeof Level>;
			division: InstanceType<typeof Division>;
		}) => this;
		return new ctor({ level: forkedLevel, division: forkedDivision });
	}

	resolve(duration: {
		noteDuration: number;
		sustainDuration: OneOrMany<number> | undefined;
	}) {
		return multiMap(combine, {
			level: this.level.resolve(duration),
			division: this.division.resolve(duration),
			...duration,
		});
	}
}

function combine({
	noteDuration,
	sustainDuration,
	level = Level.default({ noteDuration, sustainDuration }),
	division = Division.default({ noteDuration, sustainDuration }),
}: {
	noteDuration: number;
	sustainDuration: number | undefined;
	level: number[] | undefined;
	division: T_Division.uniform.absolute[] | undefined;
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
