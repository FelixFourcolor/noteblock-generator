import { mapKeys, mapValues } from "lodash";
import { JSON_SCHEMA_PREFIX as PREFIX } from "./translateRefs";

export function minimizeRefs(obj: unknown) {
	const refs = extractRefs(obj);
	const minimizedRefs = new Map(Array.from(refs).map((ref, i) => [ref, i]));
	return minimize(obj, minimizedRefs);
}

function minimize(node: unknown, refsMap: Map<string, unknown>): unknown {
	if (Array.isArray(node)) {
		return node.map((item) => minimize(item, refsMap));
	}

	if (node && typeof node === "object") {
		return mapValues(
			mapKeys(node, (_, key) => refsMap.get(key) ?? key),
			(value, key) => {
				if (key === "$ref") {
					const refKey = (value as string).slice(PREFIX.length);
					return `${PREFIX}${refsMap.get(refKey) ?? refKey}`;
				}
				return minimize(value, refsMap);
			},
		);
	}

	return node;
}

function extractRefs(node: unknown, __acc = new Set<string>()) {
	if (Array.isArray(node)) {
		node.forEach((child) => {
			extractRefs(child, __acc);
		});
	}
	if (node && typeof node === "object") {
		Object.entries(node).forEach(([key, value]) => {
			if (key === "$ref") {
				__acc.add(value.slice(PREFIX.length));
			} else {
				extractRefs(value, __acc);
			}
		});
	}
	return __acc;
}
