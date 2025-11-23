import { UserError } from "#cli/error.js";
import { assemble } from "#core/assembler/@";
import { type Building, build, cachedBuilder } from "#core/builder/@";
import { liveResolver, resolve } from "#core/resolver/@";
import type { FileRef, JsonData } from "#schema/@";

type Payload = Building | { error: string };

export function compile(src: FileRef | JsonData): Promise<Building>;

export function compile(
	src: FileRef,
	watch: { watchMode: "full" | "diff" },
): AsyncGenerator<Payload>;

export function compile(
	src: FileRef | JsonData,
	watch?: { watchMode: "full" | "diff" },
) {
	if (!watch) {
		return resolve(src).then(assemble).then(build);
	}

	const liveCompiler = async function* (): AsyncGenerator<Payload> {
		const build = cachedBuilder(watch.watchMode);

		for await (const resolve of liveResolver(src as FileRef)) {
			const payload = await resolve()
				.then(assemble)
				.then(build)
				.catch((error) => {
					if (error instanceof UserError) {
						return { error: error.message };
					}
					throw error;
				});

			if (payload) {
				yield payload;
			}
		}
	};
	return liveCompiler();
}
