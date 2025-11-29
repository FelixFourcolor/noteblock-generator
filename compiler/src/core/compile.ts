import { UserError } from "#cli/error.js";
import { type Building, build, cachedBuilder } from "#core/builder/@";
import { calculateLayout } from "#core/layout/@";
import { type JsonString, liveLoader, load } from "#core/loader/@";
import { cachedResolver, resolve } from "#core/resolver/@";
import type { FileRef } from "#schema/@";

export function compile(src: FileRef | JsonString): Promise<Building> {
	return load(src).then(resolve).then(calculateLayout).then(build);
}

type Payload = Building | { error: string };

export async function* liveCompiler(
	src: FileRef,
	options: { debounce: number; emit: "full" | "diff" },
): AsyncGenerator<Payload> {
	const resolve = cachedResolver();
	const build = cachedBuilder(options);

	for await (const load of liveLoader(src, options)) {
		const payload = await load()
			.then(resolve)
			.then(calculateLayout)
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
