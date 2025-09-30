import { json } from "typia";
import type { Song } from "#schema/@";
import { toJsonSchema } from "./transformer/transform.js";

export function generate() {
	const typiaSchema = json.schema<Song>();
	const jsonSchema = toJsonSchema(typiaSchema);
	process.stdout.write(`${JSON.stringify(jsonSchema)}\n`);
}
