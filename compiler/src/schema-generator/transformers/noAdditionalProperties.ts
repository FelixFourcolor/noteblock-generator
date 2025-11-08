import { mapValues } from "lodash";

export function noAdditionalProperties(node: unknown): unknown {
	if (Array.isArray(node)) {
		return node.map(noAdditionalProperties);
	}

	if (node && typeof node === "object") {
		const mappedObj = mapValues(node, noAdditionalProperties);
		if (
			("type" in mappedObj && mappedObj.type === "object") ||
			("properties" in mappedObj && mappedObj.properties)
		) {
			return { ...mappedObj, additionalProperties: false };
		}
		return mappedObj;
	}

	return node;
}
