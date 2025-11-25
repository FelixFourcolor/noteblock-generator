import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { stringify as yamlStringify } from "yaml";

export async function generateSourceFiles(voices: string[], root: string) {
	const srcDir = join(root, "src");

	if (existsSync(srcDir)) {
		console.error(
			`Directory "${srcDir}" already exists; skipping source generation.`,
		);
		return;
	}

	const indexPath = join(srcDir, "index.yaml");
	const indexData = { voices: voices.map((name) => `file://./${name}.yaml`) };
	const voicePaths = voices.map((voice) => join(srcDir, `${voice}.yaml`));

	await mkdir(srcDir, { recursive: true });
	return Promise.all([
		writeFile(indexPath, yamlStringify(indexData)),
		...voicePaths.map(async (path) => {
			await mkdir(dirname(path), { recursive: true });
			await writeFile(path, "[]\n");
		}),
	]);
}
