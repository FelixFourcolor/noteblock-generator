import { mkdirSync, writeFileSync } from "node:fs";
import { generateSchema } from "#utils/schema-generator/@";

export function setupSchema(root: string) {
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
