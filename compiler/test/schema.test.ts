import { readdirSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import Ajv from "ajv";
import { describe, expect, test } from "vitest";
import { parse as parseYAML } from "yaml";
import { generateSchema } from "@/extras/schema-generator";

describe("Schema tests", () => {
	const schema = generateSchema();
	const validate = new Ajv({ unicodeRegExp: false }).compile(schema);
	const projectsDir = join(__dirname, "data", "projects");

	for (const projectName of readdirSync(projectsDir)) {
		test.concurrent(projectName, () => {
			const projectPath = join(projectsDir, projectName);
			const sourceDir = join(projectPath, "repo", "src");

			return Promise.all(
				findSourceFiles(sourceDir).map(async (file) => {
					const content = await readFile(file, "utf-8");
					const parsed = parseYAML(content);
					const valid = validate(parsed);
					expect(valid).toBe(true);
				}),
			);
		});
	}
});

function* findSourceFiles(dir: string): Generator<string> {
	const entries = readdirSync(dir, { withFileTypes: true });

	for (const entry of entries) {
		const fullPath = join(dir, entry.name);
		if (entry.isDirectory()) {
			yield* findSourceFiles(fullPath);
		} else if (entry.name.endsWith(".yaml")) {
			yield fullPath;
		}
	}
}
