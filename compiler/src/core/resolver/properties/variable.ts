export type VariableTransformation<
	TransformType = { value: number; type: "absolute" | "relative" },
> = {
	transform: TransformType;
	duration: number | undefined;
}[];

export function parseNumber(value: string | number) {
	if (typeof value === "number") {
		return value;
	}
	return Number.parseInt(value);
}

export function parseNumericValue(value: string): {
	value: number;
	type: "relative" | "absolute";
} {
	const trimmed = value.trim();
	if (trimmed.startsWith("+") || trimmed.startsWith("-")) {
		const sign = trimmed.startsWith("+") ? 1 : -1;
		const unsigned = trimmed.slice(1).trim();
		return {
			value: sign * Number.parseInt(unsigned),
			type: "relative",
		};
	}
	return {
		value: Number.parseInt(trimmed),
		type: "absolute",
	};
}

export function uniformAbsolute(value: number): VariableTransformation {
	return [{ transform: { value, type: "absolute" }, duration: undefined }];
}

export function uniformRelative(
	value: string | number,
): VariableTransformation {
	if (typeof value === "number") {
		return [{ transform: { value, type: "relative" }, duration: undefined }];
	}
	return [{ transform: parseNumericValue(value), duration: undefined }];
}
