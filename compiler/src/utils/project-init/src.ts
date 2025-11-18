import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { stringify as yamlStringify } from "yaml";

export function generateSourceFiles(voices: string[], root: string) {
	const voicePaths = voices.map((voice) => `${root}/${voice}.yaml`);
	const indexPath = `${root}/index.yaml`;

	mkdirSync(root, { recursive: true });

	for (const path of voicePaths) {
		mkdirSync(dirname(path), { recursive: true });
		writeFileSync(path, "[]\n");
	}

	const indexData = { voices: voices.map((name) => `file://./${name}.yaml`) };
	writeFileSync(indexPath, yamlStringify(indexData));
}
