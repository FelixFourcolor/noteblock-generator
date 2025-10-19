import { readdir } from "node:fs/promises";
import { join } from "node:path";
import { describe } from "vitest";

export async function forEachProject(
	testName: string,
	testFn: (projectPath: string) => Promise<void>,
) {
	describe(testName, async () => {
		const projectsDir = join(__dirname, "..", "data", "projects");
		for (const projectName of await readdir(projectsDir)) {
			const projectPath = join(projectsDir, projectName);
			describe(projectName, () => testFn(projectPath));
		}
	});
}
