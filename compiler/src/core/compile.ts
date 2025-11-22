import { isEmpty } from "lodash";
import { UserError } from "#cli/error.js";
import { assemble } from "#core/assembler/@";
import { type Building, build } from "#core/builder/@";
import { resolve, resolveWatch } from "#core/resolver/@";
import type { FileRef, JsonData } from "#schema/@";
import { BuilderCache } from "./builder/cache.js";

export function compile(src: FileRef | JsonData): Promise<Building> {
	return resolve(src).then(assemble).then(build);
}

export async function* compileWatch(
	src: FileRef,
	output: "full" | "diff",
): AsyncGenerator<Building> {
	const cache = new BuilderCache();
	for await (const resolve of resolveWatch(src)) {
		const building = await resolve()
			.then(assemble)
			.then((song) => build(song, cache))
			.catch((error) => {
				if (error instanceof UserError) {
					console.error(error.message);
					return undefined;
				}
				throw error;
			});

		if (!building || isEmpty(building.blocks)) {
			continue;
		}

		if (output === "diff") {
			yield building;
		} else {
			yield cache.update(building);
		}
	}
}
