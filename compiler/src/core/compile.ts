import { isEmpty } from "lodash";
import { is } from "typia";
import { UserError } from "#cli/error.js";
import { assemble } from "#core/assembler/@";
import { type Building, build } from "#core/builder/@";
import { resolve } from "#core/resolver/@";
import type { FileRef, JsonData } from "#schema/@";
import { BuilderCache } from "./builder/cache.js";

interface Compiler {
	(src: FileRef | JsonData, watch?: undefined): Promise<Building>;
	(
		src: FileRef,
		watch: { watch: true; output: "full" | "diff" },
	): AsyncGenerator<Building | UserError>;
}

export const compile = ((src, watch) => {
	if (!watch || !is<FileRef>(src)) {
		return resolve(src).then(assemble).then(build);
	}

	return (async function* (): AsyncGenerator<Building | UserError> {
		const builderCache = new BuilderCache();

		for await (const res of resolve(src, { watch: true })) {
			try {
				const song = assemble(res);
				const building = build(song, builderCache);
				if (isEmpty(building.blocks)) {
					continue;
				}

				if (watch.output === "diff") {
					yield building;
				} else {
					yield builderCache.update(building);
				}
			} catch (error) {
				if (error instanceof UserError) {
					yield error;
				} else {
					throw error;
				}
			}
		}
	})();
}) as Compiler;
