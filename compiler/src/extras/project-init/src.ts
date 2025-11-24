import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { stringify as yamlStringify } from "yaml";

export async function generateSourceFiles(voices: string[], root: string) {
	if (existsSync(root)) {
		console.error(
			`Directory "${root}" already exists; skipping source generation.`,
		);
		return;
	}

	const indexPath = `${root}/index.yaml`;
	const indexData = { voices: voices.map((name) => `file://./${name}.yaml`) };
	const voicePaths = voices.map((voice) => `${root}/${voice}.yaml`);

	await mkdir(root, { recursive: true });
	await Promise.all([
		writeFile(indexPath, yamlStringify(indexData)),
		...voicePaths.map(async (path) => {
			await mkdir(dirname(path), { recursive: true });
			await writeFile(path, "[]\n");
		}),
	]);
}
