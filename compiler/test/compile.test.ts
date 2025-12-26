import { createHash } from "node:crypto";
import { createReadStream, readdirSync } from "node:fs";
import { mkdir, rmdir, unlink, writeFile } from "node:fs/promises";
import { dirname, join, parse } from "node:path";
import { fromPairs, orderBy, toPairs } from "lodash";
import { describe, expect, test } from "vitest";
import { build } from "@/core/builder";
import { calculateLayout } from "@/core/layout";
import { load } from "@/core/loader";
import { resolveSong } from "@/core/resolver";
import { ResolverCache } from "@/core/resolver/cache";
import type { FileRef } from "@/types/schema";

describe("Compile tests", () => {
	const projectsDir = join(__dirname, "data", "projects");
	for (const projectName of readdirSync(projectsDir)) {
		const projectPath = join(projectsDir, projectName);
		const entryFile = join(projectPath, "repo", "src", "index.yaml");
		const receivedDir = join(projectPath, "received");

		test.concurrent(projectName, async () => {
			await rmdir(receivedDir, { recursive: true }).catch(() => null);
			const compiledData = await getCompiledData(entryFile);

			const testResults = await Promise.all(
				Object.entries(compiledData).map(async ([name, data]) => {
					const getVerifiedHash = async () => {
						const verifiedFile = join(projectPath, "verified", `${name}.json`);
						return getFileHash(verifiedFile).catch(() => null);
					};

					// If verified file doesn't exist, still write the received file.
					// Convenient to generate initial snapshot.
					const writeReceivedFile = async () => {
						const receivedFile = join(receivedDir, `${name}.json`);
						await serialize(data, receivedFile);
						return receivedFile;
					};

					const [verifiedHash, receivedFile] = await Promise.all([
						getVerifiedHash(),
						writeReceivedFile(),
					]);

					if (verifiedHash === null) {
						return true;
					}

					const receivedHash = await getFileHash(receivedFile);
					const hashesMatch = verifiedHash === receivedHash;
					if (hashesMatch) {
						await unlink(receivedFile);
					}
					return hashesMatch;
				}),
			);

			expect(testResults.every((result) => result === true)).toBe(true);
			// dir is only deleted if all tests pass
			await rmdir(receivedDir).catch(() => null);
		});
	}
});

async function getCompiledData(src: string): Promise<Record<string, object>> {
	const cache = new ResolverCache();
	const data = await load(`file://${src}` as FileRef);
	const resolved = await resolveSong(data, cache).then(
		({ ticks, width, type }) => ({ ticks: Array.from(ticks), width, type }),
	);
	const layout = calculateLayout(resolved);
	const compiled = build(layout);
	const voices = Object.fromEntries(
		cache
			.exportData()
			.map(([url, res]) => [
				`resolved.${parse(url.slice("file://".length)).name}`,
				res,
			]),
	);
	return { ...voices, resolved, layout, compiled };
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
