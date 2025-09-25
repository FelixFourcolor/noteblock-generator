import { assert, is } from "typia";
import type { Beat, Duration } from "#types/schema/@";
import type { Int } from "#types/utils/@";

export function parseDuration(
	duration: Duration.determinate,
	beat: Beat,
): Int<0>;
export function parseDuration(
	duration: Duration,
	beat: Beat,
): Int<0> | undefined;
export function parseDuration(duration: Duration, beat: Beat) {
	if (is<Duration.indeterminate>(duration)) {
		return undefined;
	}

	let totalDuration = 0;
	let currentSign: 1 | -1 = 1;

	let parts = duration.split(/\s*(?=[+-])/);
	if (parts.length === 1) {
		parts = duration.split(/\s+/);
	}
	parts = parts.filter((part) => part.trim().length > 0);

	for (const part of parts) {
		let partValue = part;
		if (partValue.startsWith("+")) {
			currentSign = 1;
			partValue = partValue.slice(1);
		} else if (partValue.startsWith("-")) {
			currentSign = -1;
			partValue = partValue.slice(1);
		}

		const match = assert<(string | undefined)[]>(
			partValue.match(/(\d+)(b|B)?(\.)?/),
		);
		const [_, numberStr, beatMarker, dotMarker] = match;
		let value = Number.parseInt(assert<string>(numberStr));
		if (beatMarker) {
			value = beat * value;
		}
		if (dotMarker) {
			value = value * 1.5;
		}

		totalDuration += currentSign * value;
	}

	return Math.max(Math.floor(totalDuration), 0);
}

export function splitTimedValue(timedValue: string): {
	value: string;
	duration: Duration | undefined;
} {
	const colonIndex = timedValue.indexOf(":");
	if (colonIndex === -1) {
		return { value: timedValue.trim(), duration: undefined };
	}
	const value = timedValue.slice(0, colonIndex).trim();
	const duration = timedValue.slice(colonIndex + 1).trim();
	return { value, duration };
}

export function resolveTimedValue(
	timedValue: string,
	beat: Beat,
): {
	value: string;
	duration: number | undefined;
} {
	const { value, duration } = splitTimedValue(timedValue);
	return {
		value,
		duration: duration ? parseDuration(duration, beat) : beat,
	};
}

export function splitVariableValue(
	variableValue: string,
): { value: string; duration: Duration | undefined }[] {
	return variableValue
		.split(";")
		.map((part) => part.trim())
		.filter((part) => part.length > 0)
		.map(splitTimedValue);
}

export function resolveVariableValue(
	variableValue: string,
	beat: Beat,
): { value: string; duration: number | undefined }[] {
	return splitVariableValue(variableValue).map(({ value, duration }) => ({
		value,
		duration: duration ? parseDuration(duration, beat) : 1,
	}));
}
