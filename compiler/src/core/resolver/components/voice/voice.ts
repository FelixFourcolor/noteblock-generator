import { equals } from "typia";
import type { LazyVoice } from "@/core/loader";
import type { IProperties, Time, TPosition, Voice } from "@/types/schema";
import type { SongContext } from "../song/voices";
import type { Tick } from "../tick";
import { Context } from "../utils/context";
import { resolveNotes } from "./notes";

export type VoiceContext = SongContext & {
	index: number | [number, number];
};

export type VoiceResolution = {
	type: TPosition;
	ticks: Generator<Tick>;
	time: Time;
};

export async function resolveVoice(
	{ load }: LazyVoice,
	songModifier: IProperties,
	index: number | [number, number],
): Promise<VoiceResolution> {
	const fallbackName = `Voice ${index}`;
	const loadResult = await load();
	if ("error" in loadResult) {
		const { error } = loadResult;
		const time = NaN;
		const type = "single";
		const ticks = (function* () {
			const measure = { bar: 1, tick: 0 };
			const voice = loadResult.context?.name ?? fallbackName;
			yield [{ measure, error, voice }];
		})();
		return { time, type, ticks };
	}
	const { notes, modifier, name = fallbackName } = loadResult;

	const level = typeof index === "number" ? index : index[0];
	const context = new Context(name)
		.transform({ level })
		.transform(songModifier)
		.fork(modifier);

	const type = equals<Voice<"single">>({ notes, ...modifier })
		? ("single" as const)
		: ("double" as const);

	const { time } = context.resolveStatic();

	const ticks = resolveNotes(notes, context);

	return { time, type, ticks };
}
