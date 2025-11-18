import { existsSync, mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { stringify as yamlStringify } from "yaml";
import { UserError } from "#cli/error.js";
import { generateSchema } from "#schema-generator/generate.js";

export function initProject(voices: string[], root = ".") {
	ensureDirectoryIsEmpty(root);
	generateSourceFiles(voices, `${root}/src`);
	setupSchema(root);
}

function generateSourceFiles(voices: string[], root: string) {
	const voicePaths = voices.map((voice) => `${root}/${voice}.yaml`);
	const indexPath = `${root}/index.yaml`;

	mkdirSync(root, { recursive: true });

	for (const path of voicePaths) {
		mkdirSync(dirname(path), { recursive: true });
		writeFileSync(path, "[]\n");
	}

	const indexData = { voices: voices.map((name) => `file://./${name}.yaml`) };
	writeFileSync(indexPath, yamlStringify(indexData));
}

function ensureDirectoryIsEmpty(path: string) {
	if (!existsSync(path)) {
		return;
	}
	if (readdirSync(path).length > 0) {
		throw new UserError(`"${path}" is not empty.`);
	}
}

function setupSchema(root: string) {
	const schema = generateSchema();
	writeFileSync(`${root}/schema.json`, `${JSON.stringify(schema)}\n`);
	mkdirSync(`${root}/.vscode`, { recursive: true });
	const settings = {
		"yaml.schemas": { "schema.json": ["src/**/*.yaml"] },
	};
	writeFileSync(
		`${root}/.vscode/settings.json`,
		`${JSON.stringify(settings, null, 2)}\n`,
	);
}
