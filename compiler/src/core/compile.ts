import { UserError } from "#cli/error.js";
import { assemble } from "#core/assembler/@";
import { type Building, build, cachedBuilder } from "#core/builder/@";
import { liveResolver, resolve } from "#core/resolver/@";
import type { FileRef, JsonData } from "#schema/@";

export function compile(src: FileRef | JsonData): Promise<Building> {
	return resolve(src).then(assemble).then(build);
}

type Payload = Building | { error: string };

export async function* liveCompiler(
	src: FileRef,
	emitMode: "full" | "diff",
): AsyncGenerator<Payload> {
	const build = cachedBuilder(emitMode);
	for await (const resolve of liveResolver(src as FileRef)) {
		const payload = await resolve()
			.then(assemble)
			.then(build)
			.catch((error) => {
				if (!(error instanceof UserError)) {
					throw error;
				}
				return { error: error.message };
			});
		if (payload) {
			yield payload;
		}
	}
}
