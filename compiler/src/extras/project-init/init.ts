import { setupSchema } from "./schema.js";
import { generateSourceFiles } from "./src.js";

export async function initProject(root = ".", voices: string[] = []) {
	await Promise.all([generateSourceFiles(voices, root), setupSchema(root)]);
}
