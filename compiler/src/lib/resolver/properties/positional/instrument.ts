import { range } from "lodash";
import { match, P } from "ts-pattern";
import { assert, createIs, is } from "typia";
import { UserError } from "#cli/error.js";

import type {
	Pitch,
	Instrument as T_Instrument,
	Transpose as T_Transpose,
	Trill,
} from "#lib/schema/types/@";
import type { Int } from "#lib/schema/types/utils/@";
import { Positional } from "../positional.js";
import { Transpose } from "./transpose.js";

export type NoteBlock = {
	instrument: instrument.Name;
	note: instrument.NoteValue;
};

function createNoteBlock(value: number, instrumentName: instrument.Name) {
	return {
		instrument: instrumentName,
		note: instrument.toNoteValue(value, instrumentName),
	} satisfies NoteBlock;
}

export const Instrument = Positional({
	Default: "harp" as T_Instrument,

	resolve: (
		current,
		{
			pitch,
			trill = pitch,
			transpose = Transpose.default().transpose,
			autoTranspose = Transpose.default().autoTranspose,
		}: {
			pitch: Pitch;
			trill: Trill.Value | undefined;
			transpose: T_Transpose.absolute | undefined;
			autoTranspose: T_Transpose.Auto | undefined;
		},
	): { main: NoteBlock; trill: NoteBlock } => {
		const instrumentChoices = assert<instrument.Name[]>(
			current.split("|").map((s) => s.trim()),
		);
		const defaultInstrument = assert<instrument.Name>(instrumentChoices[0]);
		const defaultOctave = instrument.octaves[defaultInstrument];
		const resolvedPitch = resolvePitch(pitch, defaultOctave);
		if (!resolvedPitch) {
			throw new UserError(
				`Unable to resolve pitch ${pitch} for ${defaultInstrument}`,
			);
		}

		const mainValue = transpose + pitches.getValue(resolvedPitch);
		const trillValue = match(trill)
			.with(P.boolean, (trill) => mainValue + (trill ? 2 : 0))
			.with(P.number, (trill) => mainValue + trill)
			.otherwise((trill) => {
				const resolvedTrill = resolvePitch(trill, defaultOctave);
				if (!resolvedTrill) {
					throw new UserError(
						`Unable to resolve trill ${trill} for ${defaultInstrument}`,
					);
				}
				return transpose + pitches.getValue(resolvedTrill);
			});

		if (autoTranspose) {
			const transposedResult = findAutoTranspose(
				mainValue,
				trillValue,
				defaultInstrument,
			);
			if (!transposedResult) {
				throw new UserError(`Trill ${trill} on ${resolvedPitch} is impossible`);
			}
			return transposedResult;
		}

		const mainInstrument = findInstrument(mainValue, instrumentChoices);
		if (!mainInstrument) {
			throw new UserError(
				`Pitch ${resolvedPitch} is out of range for ${current}`,
			);
		}

		const trillInstrument = findInstrument(trillValue, instrumentChoices);
		if (!trillInstrument) {
			throw new UserError(
				`Trill ${trill} on ${resolvedPitch} is out of range for ${current}`,
			);
		}

		return {
			main: createNoteBlock(mainValue, mainInstrument),
			trill: createNoteBlock(trillValue, trillInstrument),
		};
	},
});

function resolvePitch(
	pitch: Pitch,
	defaultOctave: pitches.Octave,
): Pitch.absolute | undefined {
	return match(pitch)
		.with(P.when(createIs<Pitch.absolute>()), (pitch) => pitch)
		.with(P.when(createIs<Pitch.relative>()), (pitch) => {
			const octave = defaultOctave + (pitch.endsWith("^") ? 1 : -1);
			if (!is<pitches.Octave>(octave)) {
				return undefined;
			}
			return resolvePitch(pitch.slice(0, -1), octave);
		})
		.otherwise((pitch) => `${pitch}${defaultOctave}`);
}

function findInstrument(value: number, instrumentChoices: instrument.Name[]) {
	for (const instrumentName of instrumentChoices) {
		if (instrument.isInRange(value, instrumentName)) {
			return instrumentName;
		}
	}
}

function findAutoTranspose(
	mainValue: number,
	trillValue: number,
	instrumentName: instrument.Name,
) {
	const range = instrument.ranges[instrumentName];

	const minTransposeForMain = Math.ceil((range.min - mainValue) / 12);
	const maxTransposeForMain = Math.floor((range.max - mainValue) / 12);

	const minTransposeForTrill = Math.ceil((range.min - trillValue) / 12);
	const maxTransposeForTrill = Math.floor((range.max - trillValue) / 12);

	const minTranspose = Math.max(minTransposeForMain, minTransposeForTrill);
	const maxTranspose = Math.min(maxTransposeForMain, maxTransposeForTrill);
	if (minTranspose > maxTranspose) {
		return undefined;
	}

	const bestTranspose = (() => {
		if (minTranspose <= 0 && 0 <= maxTranspose) {
			return 0;
		}
		return minTranspose > 0 ? minTranspose : maxTranspose;
	})();

	const transposedMainValue = mainValue + 12 * bestTranspose;
	const transposedTrillValue = trillValue + 12 * bestTranspose;

	return {
		main: createNoteBlock(transposedMainValue, instrumentName),
		trill: createNoteBlock(transposedTrillValue, instrumentName),
	};
}

namespace pitches {
	export type Octave = Int<typeof MIN_OCTAVE, typeof MAX_OCTAVE>;

	export const getValue = (pitch: Pitch.absolute) => {
		const value = values.get(pitch.toLowerCase());
		if (value == null) {
			// should've been caught by the validator
			throw new Error(`Unrecognized pitch: ${pitch}`);
		}
		return value;
	};

	// biome-ignore format: preserve manual formatting
	const BASE_PITCHES = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"];
	const MIN_OCTAVE = 1;
	const MAX_OCTAVE = 7;
	function getBasePitches() {
		return Object.fromEntries(BASE_PITCHES.map((note, value) => [note, value]));
	}
	function addAccidentals(basePitches: Record<string, number>) {
		const base = Object.entries(basePitches);
		const withAccidentals = base
			.filter(([pitch]) => !pitch.endsWith("#lib/"))
			.flatMap(([name, value]) => [
				[`${name}#`, value + 1],
				[`${name}##`, value + 2],
				[`${name}s`, value + 1],
				[`${name}ss`, value + 2],
				[`${name}b`, value - 1],
				[`${name}bb`, value - 2],
			]);
		return Object.fromEntries([...base, ...withAccidentals]);
	}
	function expandOctaves(pitches: Record<string, number>) {
		return new Map(
			range(MIN_OCTAVE, MAX_OCTAVE + 1).flatMap((octave) =>
				Object.entries(pitches).map(([pitch, value]) => [
					`${pitch}${octave}`,
					value + 12 * (octave - 1),
				]),
			),
		);
	}
	const values = expandOctaves(addAccidentals(getBasePitches()));
}

namespace instrument {
	export type Name = keyof typeof octaves;
	export type NoteValue = Int<0, 24>;

	export const octaves = {
		bass_drum: 2,
		hat: 2,
		snare: 2,
		bass: 2,
		didgeridoo: 2,
		guitar: 3,
		banjo: 4,
		bit: 4,
		harp: 4,
		iron_xylophone: 4,
		pling: 4,
		cow_bell: 5,
		flute: 5,
		bell: 6,
		chime: 6,
		xylophone: 6,
	} as const;

	export const ranges = (() => {
		function range(from: string, to: string) {
			return { min: pitches.getValue(from), max: pitches.getValue(to) };
		}
		return Object.fromEntries(
			Object.entries(octaves).map(([instrument, octave]) => [
				instrument,
				range(`F#${octave - 1}`, `F#${octave + 1}`),
			]),
		) as Record<Name, { min: number; max: number }>;
	})();

	export function isInRange(value: number, instrumentName: Name): boolean {
		const range = ranges[instrumentName];
		return value >= range.min && value <= range.max;
	}

	export function toNoteValue(
		pitchValue: number,
		instrumentName: Name,
	): NoteValue {
		const range = ranges[instrumentName];
		return assert<NoteValue>(pitchValue - range.min);
	}
}
