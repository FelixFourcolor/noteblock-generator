import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { launchCLI } from "#cli/cli.js";

export async function setupSchema(root: string) {
	const generateSchema = (async () => {
		if (existsSync(`${root}/schema.json`)) {
			console.error("Schema file already exists; skipping schema generation.");
			return;
		}
		await launchCLI(["schema", "--out", schemaFile]);
	})();

	const setupVSCode = (async () => {
		if (existsSync(`${root}/.vscode`)) {
			console.error("Directory .vscode already exists; skipping VSCode setup.");
			return;
		}
		const settings = { "yaml.schemas": { "schema.json": ["src/**/*.yaml"] } };
		await mkdir(`${root}/.vscode`, { recursive: true });
		await writeFile(
			`${root}/.vscode/settings.json`,
			`${JSON.stringify(settings, null, 2)}\n`,
		);
	})();

	await Promise.all([generateSchema, setupVSCode]);
}
