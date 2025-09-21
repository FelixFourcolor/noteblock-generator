import { match, P } from "ts-pattern";
import { assert, createIs } from "typia";
import { parseDuration } from "#core/resolver/duration.js";
import type { Beat, Duration, Sustain as T_Sustain } from "#core/types/@";
import { Positional } from "../positional.js";

export const Sustain = Positional({
	Default: -1,

	transform: (
		current: boolean | number,
		modifier: T_Sustain,
		{ beat }: { beat: Beat },
	) =>
		match(parse(modifier, beat))
			.with(P.boolean, (transform) => transform)
			.with({ type: "absolute" }, ({ value }) => value)
			.with({ type: "relative" }, ({ value }) =>
				match(current)
					.with(P.number, (current) => {
						const transformed = current + value;
						if (current < 0 && transformed >= 0) {
							return true;
						}
						if (current >= 0 && transformed < 0) {
							return false;
						}
						return transformed;
					})
					.with(false, () => {
						const transformed = 1 + value;
						if (transformed < 0) {
							return false;
						}
						return transformed;
					})
					.otherwise(() => {
						if (value < 0) {
							return value;
						}
						return true;
					}),
			)
			.exhaustive(),

	resolve: (current, { noteDuration }: { noteDuration: number }) =>
		match(current)
			.with(P.boolean, (current) => (current ? noteDuration : 1))
			.with(P.number.positive(), (current) => Math.min(noteDuration, current))
			.with(P.number.negative(), (current) =>
				Math.max(1, noteDuration + current),
			)
			.otherwise(() => 1),
});

function parse(
	modifier: T_Sustain,
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
		.with(P.when(createIs<T_Sustain.relative>()), (modifier) => {
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
