export type VariableTransformation<
	TransformType = { value: number; type: "absolute" | "relative" },
> = {
	transform: TransformType;
	duration: number | undefined;
}[];

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
			type: "relative" as const,
		};
	}
	return {
		value: Number.parseInt(trimmed),
		type: "absolute" as const,
	};
}

export function uniformAbsolute(value: number): VariableTransformation {
	return [{ transform: { value, type: "absolute" }, duration: undefined }];
}
export function uniformRelative(value: string): VariableTransformation {
	return [{ transform: parseNumericValue(value), duration: undefined }];
}
