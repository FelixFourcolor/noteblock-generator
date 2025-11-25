import { existsSync, readdirSync } from "node:fs";
import { realpath } from "node:fs/promises";
import { UserError } from "#cli/error.js";
import { setupSchema } from "./schema.js";
import { generateSourceFiles } from "./src.js";

export function initProject(root = ".", voices: string[] = []) {
	return Promise.all([generateSourceFiles(voices, root), setupSchema(root)]);
}
