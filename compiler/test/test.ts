import { readdir } from "node:fs/promises";
import { join } from "node:path";
import { describe } from "vitest";

export async function forEachProject(
	name: string,
	test: (projectDir: string) => Promise<void>,
) {
	describe(name, async () => {
		const dataDir = join(__dirname, "data");
		for (const projectName of await readdir(dataDir)) {
			const projectDir = join(dataDir, projectName);
			describe(projectName, () => test(projectDir));
		}
	});
}
