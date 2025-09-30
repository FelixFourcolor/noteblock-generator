import { mapKeys, mapValues } from "lodash";

export function translateRefs(node: unknown): unknown {
	if (Array.isArray(node)) {
		return node.map(translateRefs);
	}

	if (node && typeof node === "object") {
		return mapValues(sanitizeKeys(node), (value, key) => {
			if (key !== "$ref") {
				return translateRefs(value);
			}
			return withPrefix(
				sanitizeString,
				OPEN_API_PREFIX,
				JSON_SCHEMA_PREFIX,
			)(value);
		});
	}

	return node;
}

function sanitizeKeys(obj: object) {
	return mapKeys(obj, (_, key) => sanitizeString(key));
}

function sanitizeString(str: string) {
	return str
		.replace(/\.\.\./g, "_ellipsis_")
		.replace(/[\\/[\]{}()<>'"*#+-]/g, "_")
		.replace(/\bs\*/g, "s_star")
		.replace(/\bd\*/g, "d_star")
		.replace(/\bb\*/g, "b_star")
		.replace(/_+/g, "_")
		.replace(/^_|_$/g, "");
}

function withPrefix(
	transform: (str: string) => string,
	prefix: string,
	newPrefix = prefix,
) {
	return (str: string) => {
		if (!str.startsWith(prefix)) {
			return transform(str);
		}
		const suffix = str.slice(prefix.length);
		return `${newPrefix}${transform(suffix)}`;
	};
}

const OPEN_API_PREFIX = "#/components/schemas/";
const JSON_SCHEMA_PREFIX = "#/$defs/";
