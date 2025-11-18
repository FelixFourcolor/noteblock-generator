import { assemble } from "#core/assembler/@";
import { build } from "#core/builder/@";
import { resolve } from "#core/resolver/@";
import type { FileRef, JsonData } from "#schema/@";

export function compile(src: FileRef | JsonData) {
	return resolve(src).then(assemble).then(build);
}

export async function compileAll(src: FileRef | JsonData) {
	const resolved = await resolve(src);
	const assembled = assemble(resolved);
	const compiled = build(assembled);
	return { resolved, assembled, compiled };
}
