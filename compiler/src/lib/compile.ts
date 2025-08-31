import { assemble } from "#lib/assembler/@";
import { type BuildingDTO, build } from "#lib/builder/@";
import { resolve } from "#lib/resolver/@";
import type { FileRef, JsonData } from "#lib/schema/types/@";

export function compile(src: FileRef | JsonData): Promise<BuildingDTO> {
	return resolve(src).then(assemble).then(build);
}
