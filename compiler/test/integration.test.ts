import { readdir, readFile, unlink } from "node:fs/promises";
import { join } from "node:path";
import { describe, expect, test } from "vitest";
import { CLI } from "../dist/cli/cli.js";

const TEST_DATA_DIR = join(__dirname, "test-data/data");

const COMPILE_MODES = [
	{ mode: "resolve", outputName: "resolved" },
	{ mode: "assemble", outputName: "assembled" },
	{ mode: "compile", outputName: "compiled" },
] as const;

describe("Integration tests", async () => {
	const testCases = await readdir(TEST_DATA_DIR);
	for (const testFolder of testCases) {
		const testDir = join(TEST_DATA_DIR, testFolder);

		describe(`Test case: ${testFolder}`, () => {
			for (const { mode, outputName } of COMPILE_MODES) {
				test(`Mode: ${mode}`, async () => {
					const entryPoint = join(testDir, "src/index.yaml");
					const receivedFile = join(
						testDir,
						`build/${outputName}.received.json`,
					);
					const expectedFile = join(
						testDir,
						`build/${outputName}.expected.json`,
					);

					// biome-ignore format: true
					const cli = new CLI([
                        "--in", entryPoint,
                        "--debug", mode,
                        "--out", receivedFile,
                    ]);
					await cli.run();

					const received = await readFile(receivedFile, "utf-8");
					const expected = await readFile(expectedFile, "utf-8");

					expect(received).toBe(expected);
					await unlink(receivedFile);
				});
			}
		});
	}
});
