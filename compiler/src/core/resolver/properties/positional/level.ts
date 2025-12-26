import { times, zipWith } from "lodash";
import { match, P } from "ts-pattern";
import { createIs } from "typia";
import type { Level as T_Level } from "@/types/schema";
import { resolveVariableValue } from "../duration";
import { Positional } from "../positional";
import type { ResolveType } from "../properties";
import {
	parseNumericValue,
	uniformAbsolute,
	uniformRelative,
} from "../variable";
import { Sustain } from "./sustain";

export const Level = Positional({
	Default: [uniformAbsolute(0)],

	transform: (current, modifier: T_Level, { beat }: { beat: number }) => {
		return match(modifier)
			.with(P.when(createIs<T_Level.uniform>()), (modifier) => [
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
		duration: { noteDuration: number; sustain: ResolveType<typeof Sustain> },
	): number[] => {
		const { noteDuration, sustain = Sustain.default({ noteDuration }) } =
			duration;

		const transformationArray = current.map((transformations) => {
			const undefinedParts = transformations.filter(
				({ duration }) => duration === undefined,
			);
			const totalDefinedDuration = Math.min(
				sustain,
				transformations.reduce((acc, { duration }) => acc + (duration ?? 0), 0),
			);
			const impliedDuration = Math.floor(
				(sustain - totalDefinedDuration) / undefinedParts.length,
			);
			return transformations.map(({ transform, duration }) => ({
				transform,
				duration: duration ?? impliedDuration,
			}));
		});

		const sustainedPart = transformationArray.reduce<number[]>(
			(levels, transformations) => {
				const vectorizedTransformations = transformations.flatMap(
					({ transform, duration }) => times(duration, () => transform),
				);
				if (vectorizedTransformations.length > sustain) {
					vectorizedTransformations.length = sustain;
				} else if (vectorizedTransformations.length < sustain) {
					vectorizedTransformations.push(
						...times(
							sustain - vectorizedTransformations.length,
							() => ({ value: 0, type: "relative" }) as const,
						),
					);
				}

				return zipWith(
					levels,
					vectorizedTransformations,
					(current, transform) =>
						match(transform)
							.with({ type: "absolute" }, ({ value }) => value)
							.otherwise(({ value }) => current + value),
				);
			},
			times(sustain, () => 0),
		);

		const silentPart = times(noteDuration - sustain, () => 0);
		return [...sustainedPart, ...silentPart];
	},
});
