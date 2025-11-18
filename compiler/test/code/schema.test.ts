import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import Ajv from "ajv";
import { expect, test } from "vitest";
import { parse as parseYAML } from "yaml";
import { generateSchema } from "#utils/schema-generator";
import { forEachProject } from "./shared";

const schema = generateSchema();
const validate = new Ajv({ unicodeRegExp: false }).compile(schema);

forEachProject("Schema tests", async (projectDir) => {
	const srcDir = join(projectDir, "repo", "src");
	for (const srcFile of await findSourceFiles(srcDir)) {
		test(srcFile, () => {
			return readFile(srcFile, "utf-8")
				.then(parseYAML)
				.then(validate)
				.then((valid) => expect(valid).toBe(true));
		});
	}
});

async function findSourceFiles(dir: string): Promise<string[]> {
	const files = [];
	const entries = await readdir(dir, { withFileTypes: true });

	for (const entry of entries) {
		const fullPath = join(dir, entry.name);
		if (entry.isDirectory()) {
			files.push(...(await findSourceFiles(fullPath)));
		} else if (entry.name.endsWith(".yaml")) {
			files.push(fullPath);
		}
	}
	return files;
}
