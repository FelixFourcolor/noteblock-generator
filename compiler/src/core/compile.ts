import { assemble } from "#core/assembler/@";
import { build } from "#core/builder/@";
import { resolve } from "#core/resolver/@";
import type { FileRef, JsonData } from "#schema/@";

export function compile(src: FileRef | JsonData) {
	return resolve(src).then(assemble).then(build);
}
