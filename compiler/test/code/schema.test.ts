import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import Ajv from "ajv";
import { expect, test } from "vitest";
import { parse as parseYAML } from "yaml";
import { generateSchema } from "#extras/schema-generator";
import { forEachProject } from "./shared";

const schema = generateSchema();
const validate = new Ajv({ unicodeRegExp: false }).compile(schema);

forEachProject("Schema tests", (projectDir) => {
	const sourceDir = join(projectDir, "repo", "src");
	const sourceFiles = findSourceFiles(sourceDir);
	sourceFiles.forEach((file) => {
		test(file, () => {
			const content = readFileSync(file, "utf-8");
			const parsed = parseYAML(content);
			const valid = validate(parsed);
			expect(valid).toBe(true);
		});
	});
});

function findSourceFiles(dir: string): string[] {
	const files = [];
	const entries = readdirSync(dir, { withFileTypes: true });

	for (const entry of entries) {
		const fullPath = join(dir, entry.name);
		if (entry.isDirectory()) {
			files.push(...findSourceFiles(fullPath));
		} else if (entry.name.endsWith(".yaml")) {
			files.push(fullPath);
		}
	}
	return files;
}
