import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { launchCLI } from "#cli/cli.js";

export function setupSchema(root: string) {
	const vscodeDir = join(root, ".vscode");

	const generateSchema = (async () => {
		const schemaFile = join(vscodeDir, "schema.json");
		if (existsSync(schemaFile)) {
			console.error("Schema file already exists; skipping schema generation.");
			return;
		}
		await launchCLI(["schema", "--out", schemaFile]);
	})();

	const generateVscodeSettings = (async () => {
		const settingsFile = join(vscodeDir, "settings.json");
		if (existsSync(settingsFile)) {
			console.error("VSCode settings already exist; skipping schema setup.");
			return;
		}
		const settings = {
			"yaml.schemas": { ".vscode/schema.json": ["src/**/*.yaml"] },
		};
		await mkdir(vscodeDir, { recursive: true });
		await writeFile(settingsFile, `${JSON.stringify(settings, null, 2)}\n`);
	})();

	return Promise.all([generateSchema, generateVscodeSettings]);
}
