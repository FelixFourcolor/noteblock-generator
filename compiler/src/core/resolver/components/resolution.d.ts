import type { IProperties, Time, TPosition } from "#schema/@";
import type { Tick } from "./tick.js";

export type SongContext = { songModifier: IProperties; cwd: string };
export type VoiceContext = SongContext & { index: number | [number, number] };

export type VoiceResolution = {
	type: TPosition;
	ticks: Generator<Tick>;
	time: Time;
};
export type SongResolution = {
	type: TPosition;
	ticks: Tick[];
	width: number;
};
