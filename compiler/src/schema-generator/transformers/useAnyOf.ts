import { mapKeys, mapValues } from "lodash";

export function useAnyOf(node: unknown): unknown {
	if (Array.isArray(node)) {
		return node.map(useAnyOf);
	}

	if (node && typeof node === "object") {
		return mapValues(
			mapKeys(node, (_, key) => (key === "oneOf" ? "anyOf" : key)),
			useAnyOf,
		);
	}

	return node;
}
