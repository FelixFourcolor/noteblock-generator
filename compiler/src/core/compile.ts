import { isEmpty } from "lodash";
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

	let activeErrorMessage: string | undefined;
	const getPayload = (buildAsync: Promise<Building>) => {
		return buildAsync
			.then((building) => {
				if (activeErrorMessage) {
					activeErrorMessage = undefined;
					// return even if empty to clear the error message
					return building;
				}
				if (!isEmpty(building.blocks)) {
					return building;
				}
			})
			.catch((e) => {
				if (!(e instanceof UserError)) {
					throw e;
				}
				if (activeErrorMessage !== e.message) {
					activeErrorMessage = e.message;
					return { error: activeErrorMessage };
				}
			});
	};

	for await (const load of liveLoader(src, options)) {
		const buildAsync = load().then(resolve).then(calculateLayout).then(build);
		const payload = await getPayload(buildAsync);
		if (payload) {
			yield payload;
		}
	}
}
