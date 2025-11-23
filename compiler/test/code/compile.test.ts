import { createHash } from "node:crypto";
import {
	createReadStream,
	mkdirSync,
	unlinkSync,
	writeFileSync,
} from "node:fs";
import { dirname, join, parse } from "node:path";
import { fromPairs, mapKeys, orderBy, toPairs } from "lodash";
import { expect, test } from "vitest";
import { assemble } from "#core/assembler";
import { build } from "#core/builder";
import { ResolutionCache } from "#core/resolver/cache.js";
import { resolveSong } from "#core/resolver/components";
import { forEachProject } from "./shared";

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

forEachProject("Compile tests", async (projectDir) => {
	const entryFile = join(projectDir, "repo", "src", "index.yaml");
	const buildDir = join(projectDir, "build");
	const results = await getCompiledData(entryFile);

	for (const [name, data] of Object.entries(results)) {
		const receivedFile = join(buildDir, "received", `${name}.json`);
		serialize(data, receivedFile);
		// If expected file doesn't exist, still write the received file.
		// Convenient to generate initial snapshot.

		const expectedFile = join(buildDir, `${name}.json`);
		const expectedHash = await getFileHash(expectedFile).catch(() => null);
		if (!expectedHash) {
			test.skip(`expected ${name} output not found`);
			continue;
		}

		const receivedHash = await getFileHash(receivedFile);
		test(name, () => {
			expect(receivedHash).toBe(expectedHash);
			unlinkSync(receivedFile);
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

function serialize(object: object, file: string) {
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
	mkdirSync(dirname(file), { recursive: true });
	writeFileSync(file, content);
}
