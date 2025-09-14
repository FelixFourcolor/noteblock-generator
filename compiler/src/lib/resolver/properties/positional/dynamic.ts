import { times, zipWith } from "lodash";
import { match, P } from "ts-pattern";
import { createIs } from "typia";
import { resolveVariableValue } from "#lib/resolver/duration.js";
import type { Dynamic as T_Dynamic } from "#lib/schema/types/@";
import { Positional } from "../positional.js";
import {
	parseNumericValue,
	uniformAbsolute,
	uniformRelative,
} from "../variable.js";
import { Sustain } from "./sustain.js";

export const Dynamic = Positional({
	Default: [uniformAbsolute(1)],
	transform: (current, modifier: T_Dynamic, { beat }: { beat: number }) => {
		return match(modifier)
			.with(P.when(createIs<T_Dynamic.uniform.absolute>()), (modifier) => [
				uniformAbsolute(Number.parseInt(modifier)),
			])
			.with(P.when(createIs<T_Dynamic.uniform.relative>()), (modifier) => [
				...current,
				uniformRelative(modifier),
			])
			.otherwise((modifier) => [
				...current,
				resolveVariableValue(modifier, beat).map(({ value, duration }) => ({
					transform: parseNumericValue(value === "~" ? "+0" : value),
					duration,
				})),
			]);
	},

	resolve: (
		current,
		duration: { noteDuration: number; sustainDuration: number | undefined },
	): number[] => {
		const {
			noteDuration,
			sustainDuration = Sustain.default({ noteDuration }),
		} = duration;

		const transformationArray = current.map((transformations) => {
			const undefinedParts = transformations.filter(
				({ duration }) => duration === undefined,
			);
			const totalDefinedDuration = Math.min(
				sustainDuration,
				transformations.reduce((acc, { duration }) => acc + (duration ?? 0), 0),
			);
			const impliedDuration = Math.floor(
				(sustainDuration - totalDefinedDuration) / undefinedParts.length,
			);
			return transformations.map(({ transform, duration }) => ({
				transform,
				duration: duration ?? impliedDuration,
			}));
		});

		const sustainedPart = transformationArray.reduce<number[]>(
			(dynamics, transformations) => {
				const vectorizedTransformations = transformations.flatMap(
					({ transform, duration }) => times(duration, () => transform),
				);
				if (vectorizedTransformations.length > sustainDuration) {
					vectorizedTransformations.length = sustainDuration;
				} else if (vectorizedTransformations.length < sustainDuration) {
					vectorizedTransformations.push(
						...times(
							sustainDuration - vectorizedTransformations.length,
							() => ({ value: 0, type: "relative" }) as const,
						),
					);
				}

				return zipWith(
					dynamics,
					vectorizedTransformations,
					(current, transform) =>
						match(transform)
							.with({ type: "absolute" }, ({ value }) => value)
							.otherwise(({ value }) =>
								Math.max(1, Math.min(6, current + value)),
							),
				);
			},
			times(sustainDuration, () => 0),
		);

		const silentPart = times(noteDuration - sustainDuration, () => 0);

		return [...sustainedPart, ...silentPart];
	},
});
