import { is } from "typia";
import { UserError } from "#cli/error.js";
import { assemble } from "#core/assembler/@";
import { type Building, build } from "#core/builder/@";
import { resolve } from "#core/resolver/@";
import type { FileRef, JsonData } from "#schema/@";

export function compile(
	src: FileRef,
	option: { watch: true },
): AsyncGenerator<Building | UserError>;

export function compile(src: FileRef | JsonData): Promise<Building>;

export function compile(src: FileRef | JsonData, option?: { watch: true }) {
	if (!option?.watch || !is<FileRef>(src)) {
		return resolve(src).then(assemble).then(build);
	}

	return (async function* () {
		for await (const resolution of resolve(src, { watch: true })) {
			try {
				yield build(assemble(resolution));
			} catch (error) {
				if (error instanceof UserError) {
					yield error;
				} else {
					throw error;
				}
			}
		}
	})();
}
