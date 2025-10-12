import { readdir, readFile, unlink } from "node:fs/promises";
import { join } from "node:path";
import Ajv from "ajv";
import { afterAll, expect, test } from "vitest";
import { parse as parseYAML } from "yaml";
import { CLI } from "#cli";
import { forEachProject } from "../test";

const schemaFile = join(__dirname, "schema.json");
const validatePromise = CLI.run(["--schema", "--out", schemaFile])
	.then(() => readFile(schemaFile, "utf-8"))
	.then(JSON.parse)
	.then((schema) => new Ajv({ unicodeRegExp: false }).compile(schema));

forEachProject("Schema tests", async (projectDir) => {
	const srcDir = join(projectDir, "src");
	for (const srcFile of await findSourceFiles(srcDir)) {
		test(srcFile, async () => {
			await readFile(srcFile, "utf-8")
				.then(parseYAML)
				.then(await validatePromise)
				.then((valid) => expect(valid).toBe(true));
		});
	}
});

afterAll(() => unlink(schemaFile));

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
