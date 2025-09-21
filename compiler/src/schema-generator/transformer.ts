import { mapKeys, mapValues } from "lodash";
import type { IJsonSchemaUnit } from "typia";

type Json = any;

export function toJsonSchema(typiaSchema: IJsonSchemaUnit.IV3_1<unknown>) {
	return {
		$schema: "https://json-schema.org/draft-07/schema",
		$defs: transform(typiaSchema.components.schemas),
		...transform(typiaSchema.schema),
	};
}

function transform(node: Json): Json {
	const chain = <T>(value: T) => ({
		pipe: <U>(fn: (_: T) => U) => chain(fn(value)),
		get: () => value,
	});

	return chain(node)
		.pipe(translateRefsFormat)
		.pipe(convert_OneOf_to_AnyOf)
		.pipe(noAdditionalProperties)
		.get();
}

function noAdditionalProperties(obj: Json): Json {
	if (Array.isArray(obj)) {
		return obj.map(noAdditionalProperties);
	}
	if (obj && typeof obj === "object") {
		obj = mapValues(obj, noAdditionalProperties);
		if (obj.type === "object" || obj.properties) {
			return { ...obj, additionalProperties: false };
		}
	}
	return obj;
}

function convert_OneOf_to_AnyOf(node: Json): Json {
	if (Array.isArray(node)) {
		return node.map(convert_OneOf_to_AnyOf);
	}

	if (node && typeof node === "object") {
		return mapValues(
			mapKeys(node, (_, key) => (key === "oneOf" ? "anyOf" : key)),
			convert_OneOf_to_AnyOf,
		);
	}

	return node;
}

function translateRefsFormat(node: Json): Json {
	if (Array.isArray(node)) {
		return node.map(translateRefsFormat);
	}

	if (node && typeof node === "object") {
		return mapValues(sanitizeKeys(node), (value, key) => {
			if (key !== "$ref") {
				return translateRefsFormat(value);
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

function sanitizeKeys(obj: Record<string, Json>) {
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
