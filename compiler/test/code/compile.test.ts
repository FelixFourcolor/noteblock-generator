import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { unlink, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fromPairs, orderBy, toPairs } from "lodash";
import { expect, test } from "vitest";
import { compileAll } from "#core/compile";
import { forEachProject } from "./shared";

const COMPILE_MODES = ["resolved", "assembled", "compiled"] as const;

forEachProject("Compile tests", async (projectDir) => {
	const entryFile = join(projectDir, "repo", "src", "index.yaml");
	const compiledResult = await compileAll(`file://${entryFile}`);

	for (const outputMode of COMPILE_MODES) {
		const expectedFile = join(projectDir, "build", `${outputMode}.json`);
		const expectedHash = await getFileHash(expectedFile).catch(() => null);
		if (!expectedHash) {
			test.skip(`expected ${outputMode} output not found`);
			continue;
		}

		const receivedFile = join(
			projectDir,
			"build",
			`${outputMode}.received.json`,
		);
		serialize(compiledResult[outputMode], receivedFile);
		const receivedHash = await getFileHash(receivedFile);

		test(`${outputMode}`, async () => {
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

async function serialize(object: object, file: string) {
	const sortKeys = (value: unknown): unknown => {
		if (Array.isArray(value)) {
			return value.map(sortKeys);
		}
		if (value && typeof value === "object") {
			return fromPairs(
				orderBy(toPairs(value), ([key]) => key).map(([key, val]) => [
					key,
					sortKeys(val),
				]),
			);
		}
		return value;
	};

	const content = JSON.stringify(sortKeys(object), null, 2);
	await writeFile(file, content);
}
