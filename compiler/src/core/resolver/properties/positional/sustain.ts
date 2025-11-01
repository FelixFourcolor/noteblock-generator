import { match, P } from "ts-pattern";
import { assert, createIs } from "typia";
import { parseDuration } from "#core/resolver/duration.js";
import type {
	Beat,
	Duration,
	IPositional,
	Sustain as T_Sustain,
} from "#schema/@";
import { multiMap } from "../multi.js";
import { Positional } from "../positional.js";

export class Sustain {
	static default({ noteDuration }: { noteDuration: number }) {
		return noteDuration - 1;
	}

	private readonly min: InstanceType<ReturnType<typeof Value>>;
	private readonly max: InstanceType<ReturnType<typeof Value>>;
	private readonly value: InstanceType<ReturnType<typeof Value>>;

	constructor(
		args = {
			min: new (Value(1))(),
			max: new (Value(Number.MAX_SAFE_INTEGER))(),
			value: new (Value(-1))(),
		},
	) {
		this.min = args.min;
		this.max = args.max;
		this.value = args.value;
	}

	fork(modifier: IPositional<T_Sustain> | undefined, args: { beat: Beat }) {
		return new Sustain({
			min: this.min.fork(modifier?.min, args),
			max: this.max.fork(modifier?.max, args),
			value: this.value.fork(modifier?.value, args),
		});
	}

	transform(
		modifier: IPositional<T_Sustain> | undefined,
		args: { beat: Beat },
	) {
		this.min.transform(modifier?.min, args);
		this.max.transform(modifier?.max, args);
		this.value.transform(modifier?.value, args);
		return this;
	}

	resolve(args: { noteDuration: number }) {
		return multiMap(
			({ min, max, value }) => Math.min(Math.max(value, min), max),
			{
				min: this.min.resolve(args),
				max: this.max.resolve(args),
				value: this.value.resolve(args),
			},
		);
	}
}

const Value = (Default: number) => {
	return Positional({
		Default,
		transform: (
			current: boolean | number,
			modifier: T_Sustain.Value,
			{ beat }: { beat: Beat },
		) => {
			return match(parse(modifier, beat))
				.with(P.boolean, (transform) => transform)
				.with({ type: "absolute" }, ({ value }) => value)
				.with({ type: "relative" }, ({ value }) =>
					match(current)
						.with(P.number, (current) => {
							const transformed = current + value;
							if (current < 0 && transformed >= 0) {
								return true;
							}
							if (current >= 1 && transformed < 1) {
								return false;
							}
							return transformed;
						})
						.with(false, () => {
							const transformed = 1 + value;
							return transformed <= 1 ? false : transformed;
						})
						.with(true, () => {
							return value < 0 ? value : true;
						})
						.exhaustive(),
				)
				.exhaustive();
		},
		resolve: (current, { noteDuration }: { noteDuration: number }) => {
			return match(current)
				.with(P.boolean, (yes) => (yes ? noteDuration : 1))
				.with(P.number.positive(), (v) => Math.min(v, noteDuration))
				.with(P.number.negative(), (v) => Math.max(v + noteDuration, 1))
				.otherwise(() => 1);
		},
	});
};

function parse(
	modifier: T_Sustain.Value,
	beat: Beat,
): boolean | { type: "absolute" | "relative"; value: number } {
	return match(modifier)
		.with(P.boolean, (modifier) => modifier)
		.with(P.number, (modifier) => ({
			type: "absolute" as const,
			value: modifier,
		}))
		.with(P.when(createIs<Duration.determinate>()), (modifier) => ({
			type: "absolute" as const,
			value: parseDuration(modifier, beat),
		}))
		.with(P.when(createIs<T_Sustain.Value.relative>()), (modifier) => {
			const duration = modifier.match(/"([^"]+)"/)?.[1];
			const sign = modifier.trim().startsWith("+") ? 1 : -1;
			const value = parseDuration(assert<Duration.determinate>(duration), beat);
			return {
				type: "relative" as const,
				value: sign * value,
			};
		})
		.exhaustive();
}
