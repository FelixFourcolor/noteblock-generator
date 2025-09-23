import { assemble } from "#core/assembler/@";
import { type BuildingDTO, build } from "#core/builder/@";
import { resolve } from "#core/resolver/@";
import type { FileRef, JsonData } from "#types/schema/@";

export function compile(src: FileRef | JsonData): Promise<BuildingDTO> {
	return resolve(src).then(assemble).then(build);
}
