import type { SchemaObject } from "ajv";
import { json } from "typia";
import type { Song } from "#schema/@";
import { minimizeRefs } from "./transformers/minimizeRefs.js";
import { noAdditionalProperties } from "./transformers/noAdditionalProperties.js";
import { translateRefs } from "./transformers/translateRefs.js";
import { useAnyOf } from "./transformers/useAnyOf.js";

export function generateSchema(): SchemaObject {
	const schema = json.schema<Song>();
	return transform({
		$schema: "http://json-schema.org/draft-07/schema",
		$defs: schema.components.schemas,
		...schema.schema,
	});
}

function transform(value: SchemaObject) {
	return chain(value)
		.pipe(translateRefs)
		.pipe(minimizeRefs)
		.pipe(noAdditionalProperties)
		.pipe(useAnyOf)
		.get() as SchemaObject;
}

const chain = <T>(value: T) => ({
	pipe: <U>(fn: (_: T) => U) => chain(fn(value)),
	get: () => value,
});
