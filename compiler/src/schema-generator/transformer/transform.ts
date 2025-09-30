import type { IJsonSchemaUnit } from "typia";
import { useAnyOf } from "./anyOf.js";
import { chain } from "./chain.js";
import { noAdditionalProperties } from "./properties.js";
import { translateRefs } from "./refs.js";

export function toJsonSchema(typiaSchema: IJsonSchemaUnit.IV3_1<unknown>) {
	return {
		$schema: "https://json-schema.org/draft-07/schema",
		$defs: transform(typiaSchema.components.schemas),
		...(transform(typiaSchema.schema) as object),
	};
}

function transform(value: unknown) {
	return chain(value)
		.pipe(translateRefs)
		.pipe(noAdditionalProperties)
		.pipe(useAnyOf)
		.get();
}
