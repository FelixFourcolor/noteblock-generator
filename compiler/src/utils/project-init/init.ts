import { existsSync, readdirSync } from "node:fs";
import { UserError } from "#cli/error.js";
import { setupSchema } from "./schema.js";
import { generateSourceFiles } from "./src.js";

export function initProject(voices: string[], root = ".") {
	ensureDirectoryIsEmpty(root);
	generateSourceFiles(voices, `${root}/src`);
	setupSchema(root);
}

function ensureDirectoryIsEmpty(path: string) {
	if (!existsSync(path)) {
		return;
	}
	if (readdirSync(path).length > 0) {
		throw new UserError(`"${path}" is not empty.`);
	}
}
