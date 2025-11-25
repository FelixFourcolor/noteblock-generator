import type { BarLine } from "#schema/@";
import type { MutableContext } from "../context.js";
import type { Tick } from "../tick.js";

export function* resolveBarLine(
	barline: BarLine,
	context: MutableContext,
): Generator<Tick> {
	const numberMatch = barline.match(/\d+/);
	const barNumber = numberMatch ? Number.parseInt(numberMatch[0]) : undefined;
	const restEntireBar = barline.split("|").length > 2;

	const { voice, bar, tick } = context;

	const bypassError = barline.includes("!");
	if (
		!bypassError &&
		((bar !== barNumber && barNumber !== undefined) || tick !== 1)
	) {
		yield [
			{
				error: "Incorrect barline placement",
				voice,
				measure: { bar, tick },
			},
		];
	} else {
		yield [];
	}

	context.transform({ bar: barNumber || bar + 1, tick: 1 });

	if (restEntireBar) {
		const { delay, time } = context.resolveStatic();
		for (let i = time; i--; ) {
			yield [
				{
					delay,
					noteblock: undefined,
					voice,
					// measure updates each iteration, cannot factor out
					measure: context.measure,
				},
			];
			context.transform({ noteDuration: 1 });
		}
	}
}
