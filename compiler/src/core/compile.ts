import { isEmpty } from "lodash";
import { UserError } from "@/cli/error";
import type { FileRef } from "@/types/schema";
import { type Building, build, cachedBuilder } from "./builder";
import { calculateLayout } from "./layout";
import { type JsonString, liveLoader, load } from "./loader";
import { cachedResolver, resolve } from "./resolver";

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
