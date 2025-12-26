import { setupSchema } from "./schema";
import { generateSourceFiles } from "./src";

export async function initProject(root = ".", voices: string[] = []) {
	await Promise.all([generateSourceFiles(voices, root), setupSchema(root)]);
}
