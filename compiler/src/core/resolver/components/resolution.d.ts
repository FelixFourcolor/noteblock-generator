import type { IProperties, Time, TPosition } from "#schema/@";
import type { Tick } from "./tick.js";

export type SongContext = { songModifier: IProperties; cwd: string };
export type VoiceContext = SongContext & { index: number | [number, number] };

type Resolution = { type: TPosition; ticks: Generator<Tick> };
export type VoiceResolution = Resolution & { time: Time };
export type SongResolution = Resolution & { width: number };
