import { range } from "lodash";
import { match, P } from "ts-pattern";
import { assert, createIs, is } from "typia";
import { UserError } from "#cli/error.js";

import type {
	InstrumentName,
	Pitch,
	Instrument as T_Instrument,
	Trill,
} from "#schema/@";
import type { Int } from "#types/helpers/@";
import { Positional } from "../positional.js";
import { Transpose } from "./transpose.js";

export type NoteBlock = {
	instrument: InstrumentName;
	note: instrument.NoteValue;
};

type InstrumentChoice = InstrumentName | "null";

function createNoteBlock(pitch: number, instrumentChoice: InstrumentChoice) {
	if (instrumentChoice === "null") {
		return undefined;
	}
	return {
		instrument: instrumentChoice,
		note: instrument.toNoteValue(pitch, instrumentChoice),
	} satisfies NoteBlock | undefined;
}

export const Instrument = Positional({
	Default: "harp" as T_Instrument,

	resolve: (
		current,
		{
			pitch,
			trillValue: trill = pitch,
			transpose = Transpose.default().transpose,
			autoTranspose = Transpose.default().autoTranspose,
		}: {
			pitch: Pitch;
			trillValue: Trill.Value | undefined;
			transpose: number | undefined;
			autoTranspose: boolean | undefined;
		},
	): [NoteBlock | undefined, NoteBlock | undefined] => {
		const instrumentChoices = assert<InstrumentChoice[]>(
			current
				.split("|")
				.map((s) => s.trim())
				.filter(Boolean),
		);
		const defaultInstrument = instrumentChoices[0]!;
		if (defaultInstrument === "null") {
			return [undefined, undefined];
		}
		const defaultOctave = instrument.octaves[defaultInstrument];
		const resolvedPitch = pitches.resolve(pitch, defaultOctave);
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
				const resolvedTrill = pitches.resolve(trill, defaultOctave);
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

		const mainInstrument = instrument.find(mainValue, instrumentChoices);
		if (!mainInstrument) {
			throw new UserError(
				`Pitch ${resolvedPitch} is out of range for ${current}`,
			);
		}

		const trillInstrument = instrument.find(trillValue, instrumentChoices);
		if (!trillInstrument) {
			throw new UserError(
				`Trill ${trill} on ${resolvedPitch} is out of range for ${current}`,
			);
		}

		return [
			createNoteBlock(mainValue, mainInstrument),
			createNoteBlock(trillValue, trillInstrument),
		];
	},
});

function findAutoTranspose(
	mainValue: number,
	trillValue: number,
	instrumentName: InstrumentName,
): [NoteBlock | undefined, NoteBlock | undefined] | undefined {
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

	return [
		createNoteBlock(transposedMainValue, instrumentName),
		createNoteBlock(transposedTrillValue, instrumentName),
	];
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

	export function resolve(
		pitch: Pitch,
		defaultOctave: pitches.Octave,
	): Pitch.absolute | undefined {
		return match(pitch)
			.with(P.when(createIs<Pitch.absolute>()), (pitch) => pitch)
			.with(P.when(createIs<Pitch.relative>()), (pitch) => {
				const octave = defaultOctave + (pitch.endsWith("^") ? 1 : -1);
				if (!is<Octave>(octave)) {
					return undefined;
				}
				return resolve(pitch.slice(0, -1), octave);
			})
			.otherwise((pitch) => `${pitch}${defaultOctave}`);
	}

	// biome-ignore format: one line
	const BASE_PITCHES = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"];
	const MIN_OCTAVE = 0;
	const MAX_OCTAVE = 8;
	function getBasePitches() {
		return Object.fromEntries(BASE_PITCHES.map((note, value) => [note, value]));
	}
	function addAccidentals(basePitches: Record<string, number>) {
		const base = Object.entries(basePitches);
		const withAccidentals = base
			.filter(([pitch]) => !pitch.endsWith("#core/"))
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
	export type NoteValue = Int<0, 24>;

	export const octaves: Record<InstrumentName, number> = {
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
	};

	export const ranges = (() => {
		function range(from: string, to: string) {
			return { min: pitches.getValue(from), max: pitches.getValue(to) };
		}
		return Object.fromEntries(
			Object.entries(octaves).map(([instrument, octave]) => [
				instrument,
				range(`F#${octave - 1}`, `F#${octave + 1}`),
			]),
		) as Record<InstrumentName, { min: number; max: number }>;
	})();

	function isInRange(pitch: number, instrumentChoice: InstrumentChoice) {
		if (instrumentChoice === "null") {
			return true;
		}
		const range = ranges[instrumentChoice];
		return pitch >= range.min && pitch <= range.max;
	}

	export function find(value: number, instrumentChoices: InstrumentChoice[]) {
		for (const instrumentName of instrumentChoices) {
			if (isInRange(value, instrumentName)) {
				return instrumentName;
			}
		}
	}

	export function toNoteValue(pitch: number, instrumentName: InstrumentName) {
		const range = ranges[instrumentName];
		return assert<NoteValue>(pitch - range.min);
	}
}
