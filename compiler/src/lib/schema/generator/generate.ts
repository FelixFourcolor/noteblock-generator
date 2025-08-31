import { json } from "typia";
import type { Song } from "#lib/schema/types/components/@";
import { toJsonSchema } from "./transformer.js";

export function generateSchema() {
	const typiaSchema = json.schema<Song>();
	return toJsonSchema(typiaSchema);
}
