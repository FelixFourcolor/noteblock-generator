import { existsSync, readdirSync } from "node:fs";
import { realpath } from "node:fs/promises";
import { UserError } from "#cli/error.js";
import { setupSchema } from "./schema.js";
import { generateSourceFiles } from "./src.js";

export async function initProject(
	root = ".",
	voices: string[] = [],
	force = false,
) {
	if (existsSync(root) && readdirSync(root).length > 0 && !force) {
		const path = await realpath(root);
		throw new UserError(
			`Directory "${path}" is not empty; use --force to override.`,
		);
	}

	await Promise.all([
		generateSourceFiles(voices, `${root}/src`),
		setupSchema(root),
	]);
}
