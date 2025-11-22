import { UserError } from "#cli/error.js";
import { assemble } from "#core/assembler/@";
import { type Building, build, cachedBuilder } from "#core/builder/@";
import { liveResolver, resolve } from "#core/resolver/@";
import type { FileRef, JsonData } from "#schema/@";

export function compile(src: FileRef | JsonData): Promise<Building>;

export function compile(
	src: FileRef,
	watch: { watchMode: "full" | "diff" },
): AsyncGenerator<Building>;

export function compile(
	src: FileRef | JsonData,
	watch?: { watchMode: "full" | "diff" },
) {
	if (!watch) {
		return resolve(src).then(assemble).then(build);
	}

	const liveCompiler = async function* () {
		const build = cachedBuilder(watch.watchMode);

		for await (const resolve of liveResolver(src as FileRef)) {
			const building = await resolve()
				.then(assemble)
				.then(build)
				.catch((error) => {
					if (!(error instanceof UserError)) {
						throw error;
					}
					console.error(error.message);
					return undefined;
				});

			if (building) {
				yield building;
			}
		}
	};
	return liveCompiler();
}
