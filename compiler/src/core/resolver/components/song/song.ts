import { is } from "typia";
import type { LoadedSong } from "@/core/loader";
import type { IProperties, Time, TPosition } from "@/types/schema";
import type { ResolverCache } from "../../cache";
import type { Tick } from "../tick";
import { resolveVoices } from "./voices";

export type SongResolution<T extends TPosition = TPosition> = {
	type: T;
	width: number;
	ticks: Iterable<Tick>;
};

export async function resolveSong(
	{ voices, modifier }: LoadedSong,
	cache?: ResolverCache,
): Promise<SongResolution> {
	const voicesResolution = await resolveVoices(voices, modifier, cache);

	let { type } = voicesResolution;
	if (type === "single") {
		// Must check "is not single" instead of "is double",
		// because single is a subset of double
		if (!is<IProperties<"single">>(modifier)) {
			type = "double";
		}
	}

	const { time: voiceTime, ticks } = voicesResolution;
	let { time } = modifier;
	if (typeof time !== "number") {
		time = voiceTime;
	}
	const { width = resolveWidth({ time, type }) } = modifier;

	return { width, type, ticks };
}

function resolveWidth({ time, type }: { time: Time; type: TPosition }) {
	const min = 8;
	const max = type === "single" ? 16 : 12;
	const middle = 12;

	if (min <= time && time <= max) {
		return time;
	}

	for (let candidate = middle; candidate <= max; candidate++) {
		if (time % candidate === 0) {
			return candidate;
		}
	}
	for (let candidate = middle - 1; candidate >= min; candidate--) {
		if (time % candidate === 0) {
			return candidate;
		}
	}

	return max;
}
