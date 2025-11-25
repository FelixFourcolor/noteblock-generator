import { mapValues } from "lodash";

export function translateRefs(node: unknown): unknown {
	if (Array.isArray(node)) {
		return node.map(translateRefs);
	}

	if (node && typeof node === "object") {
		return mapValues(node, (value, key) => {
			if (key !== "$ref") {
				return translateRefs(value);
			}
			return replacePrefix(value, OPEN_API_PREFIX, JSON_SCHEMA_PREFIX);
		});
	}

	return node;
}

function replacePrefix(str: string, oldPrefix: string, newPrefix: string) {
	return str.startsWith(oldPrefix)
		? `${newPrefix}${str.slice(oldPrefix.length)}`
		: str;
}

const OPEN_API_PREFIX = "#/components/schemas/";
export const JSON_SCHEMA_PREFIX = "#/$defs/";
