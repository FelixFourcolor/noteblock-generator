import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { unlink } from "node:fs/promises";
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
		const expectedHash = await getFileHash(expectedFile).catch(() => null);
		if (!expectedHash) {
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

			const receivedHash = await getFileHash(receivedFile);
			expect(receivedHash).toBe(expectedHash);
			await unlink(receivedFile);
		});
	}
});

async function getFileHash(filePath: string): Promise<string> {
	return new Promise((resolve, reject) => {
		const hash = createHash("sha256");
		const stream = createReadStream(filePath);
		stream.on("data", (chunk) => hash.update(chunk));
		stream.on("end", () => resolve(hash.digest("hex")));
		stream.on("error", reject);
	});
}
