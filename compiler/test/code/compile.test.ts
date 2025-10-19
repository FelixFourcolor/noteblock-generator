import { readFile, unlink } from "node:fs/promises";
import { join } from "node:path";
import { expect, test } from "vitest";
import { CLI } from "#cli";
import { forEachProject } from "./shared";

const COMPILE_MODES = [
	{ mode: "resolve", output: "resolved" },
	{ mode: "assemble", output: "assembled" },
	{ mode: "compile", output: "compiled" },
] as const;

forEachProject("Compile tests", async (projectDir) => {
	for (const { mode, output } of COMPILE_MODES) {
		const expectedFile = join(projectDir, "build", `${output}.json`);
		const expected = await readFile(expectedFile, "utf-8").catch(() => null);
		if (!expected) {
			test.skip(`expected ${output} output not found`);
			continue;
		}

		test(`${mode}`, async () => {
			const entryPoint = join(projectDir, "repo", "src", "index.yaml");
			const receivedFile = join(projectDir, "build", `${output}.received.json`);

			await CLI.run([
				...["--in", entryPoint],
				...["--out", receivedFile],
				...["--debug", mode],
			]);

			const received = await readFile(receivedFile, "utf-8");
			expect(received).toBe(expected);
			await unlink(receivedFile);
		});
	}
});
