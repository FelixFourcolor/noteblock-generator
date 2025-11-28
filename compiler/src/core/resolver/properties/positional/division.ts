import { times, zipWith } from "lodash";
import { match, P } from "ts-pattern";
import { assert, createIs } from "typia";
import type { Division as T_Division } from "#schema/@";
import { resolveVariableValue } from "../duration.js";
import { Positional } from "../positional.js";
import type { ResolveType } from "../properties.js";
import type { VariableTransformation } from "../variable.js";
import { Sustain } from "./sustain.js";

const Default: VariableTransformation<T_Division.uniform | "~">[] = [
	[{ transform: "LR", duration: undefined }],
];

export const Division = Positional({
	Default,

	transform: (current, modifier: T_Division, { beat }: { beat: number }) => {
		return match(modifier)
			.with(P.when(createIs<T_Division.uniform.absolute>()), (modifier) => [
				[{ transform: modifier, duration: undefined }],
			])
			.with(P.when(createIs<T_Division.uniform.relative>()), (modifier) => [
				...current,
				[{ transform: modifier, duration: undefined }],
			])
			.otherwise((modifier) => [
				...current,
				resolveVariableValue(modifier, beat).map(({ value, duration }) => ({
					transform: assert<T_Division.uniform | "~">(value),
					duration,
				})),
			]);
	},

	resolve: (
		current,
		duration: { noteDuration: number; sustain: ResolveType<typeof Sustain> },
	): T_Division.uniform.absolute[] => {
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

		const sustainedPart = transformationArray.reduce<
			T_Division.uniform.absolute[]
		>(
			(divisions, transformations) => {
				const vectorizedTransformations = transformations.flatMap(
					({ transform, duration }) => times(duration, () => transform),
				);
				if (vectorizedTransformations.length > sustain) {
					vectorizedTransformations.length = sustain;
				} else if (vectorizedTransformations.length < sustain) {
					vectorizedTransformations.push(
						...times(
							sustain - vectorizedTransformations.length,
							() => "~" as const,
						),
					);
				}

				return zipWith(
					divisions,
					vectorizedTransformations,
					(current, transform) =>
						match(transform)
							.with("~", () => current)
							.with(P.union("L", "R", "LR"), (transform) => transform)
							.otherwise(() =>
								match(current)
									.with("L", () => "R" as const)
									.with("R", () => "L" as const)
									.otherwise(() => "LR" as const),
							),
				);
			},
			times(sustain, () => "LR" as const),
		);

		const silentPart = times(noteDuration - sustain, () => "LR" as const);
		return [...sustainedPart, ...silentPart];
	},
});
