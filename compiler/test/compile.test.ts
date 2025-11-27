import { createHash } from "node:crypto";
import { createReadStream, readdirSync } from "node:fs";
import { mkdir, unlink, writeFile } from "node:fs/promises";
import { dirname, join, parse } from "node:path";
import { fromPairs, mapKeys, orderBy, toPairs } from "lodash";
import { describe, expect, test } from "vitest";
import { assemble } from "#core/assembler";
import { build } from "#core/builder";
import { ResolutionCache } from "#core/resolver/cache.js";
import { resolveSong } from "#core/resolver/components";

describe("Compile tests", () => {
	const projectsDir = join(__dirname, "data", "projects");
	for (const projectName of readdirSync(projectsDir)) {
		const projectPath = join(projectsDir, projectName);

		test.concurrent(projectName, async () => {
			const entryFile = join(projectPath, "repo", "src", "index.yaml");
			const results = await getCompiledData(entryFile);

			return Promise.all(
				Object.entries(results).map(async ([name, data]) => {
					const getVerifiedHash = async () => {
						const verifiedFile = join(projectPath, "verified", `${name}.json`);
						return getFileHash(verifiedFile).catch(() => null);
					};

					// If verified file doesn't exist, still write the received file.
					// Convenient to generate initial snapshot.
					const writeReceivedFile = async () => {
						const receivedFile = join(projectPath, "received", `${name}.json`);
						await serialize(data, receivedFile);
						return receivedFile;
					};

					const [verifiedHash, receivedFile] = await Promise.all([
						getVerifiedHash(),
						writeReceivedFile(),
					]);

					if (verifiedHash === null) {
						return;
					}

					const receivedHash = await getFileHash(receivedFile);
					expect(receivedHash).toBe(verifiedHash);
					await unlink(receivedFile);
				}),
			);
		});
	}
});

async function getCompiledData(src: string): Promise<Record<string, object>> {
	const cache = new ResolutionCache();
	const rawResolved = await resolveSong(`file://${src}`, cache);
	const resolved = { ...rawResolved, ticks: Array.from(rawResolved.ticks) };
	const assembled = assemble(resolved);
	const compiled = build(assembled);
	const voices = mapKeys(
		cache.exportData(),
		(_, path) => `resolved.${parse(path).name}`,
	);
	return { ...voices, resolved, assembled, compiled };
}

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
	await mkdir(dirname(file), { recursive: true });
	await writeFile(file, content);
}
