import { mapValues } from "lodash";

export function noAdditionalProperties(obj: unknown): unknown {
	if (Array.isArray(obj)) {
		return obj.map(noAdditionalProperties);
	}

	if (obj && typeof obj === "object") {
		const mappedObj = mapValues(obj, noAdditionalProperties);
		if (
			("type" in mappedObj && mappedObj.type === "object") ||
			("properties" in mappedObj && mappedObj.properties)
		) {
			return { ...mappedObj, additionalProperties: false };
		}
	}

	return obj;
}
