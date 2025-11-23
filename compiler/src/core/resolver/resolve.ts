import { basename, dirname } from "node:path";
import { watch } from "chokidar";
import { resolveSong, type SongResolution } from "#core/resolver/components/@";
import type { FileRef, JsonData } from "#schema/@";
import { ResolutionCache } from "./cache.js";

export function resolve(src: FileRef | JsonData): Promise<SongResolution> {
	return resolveSong(src);
}

type Resolver = () => Promise<SongResolution>;

export async function* liveResolver(src: FileRef): AsyncGenerator<Resolver> {
	const entryFilePath = src.slice(7);
	const trackedDependencies = new Set<string>();
	const changedFiles = new Set([entryFilePath]);
	const cache = new ResolutionCache();

	let { nextChange, signalChange } = createChangeSignal();
	const watcher = watch(basename(entryFilePath), {
		cwd: dirname(entryFilePath),
	});
	watcher.on("change", (filePath) => {
		changedFiles.add(filePath);
		signalChange();
	});

	try {
		while (true) {
			if (changedFiles.size === 0) {
				await nextChange;
				({ nextChange, signalChange } = createChangeSignal());
			}

			changedFiles.forEach((filePath) => {
				cache.invalidate(filePath);
			});
			changedFiles.clear();

			yield async () => {
				const resolution = await resolveSong(src, cache);
				cache.dependencies.forEach((path) => {
					if (!trackedDependencies.has(path)) {
						watcher.add(path);
						trackedDependencies.add(path);
					}
				});
				return resolution;
			};
		}
	} finally {
		watcher.close();
	}
}

function createChangeSignal() {
	const { promise, resolve } = Promise.withResolvers<void>();
	return { nextChange: promise, signalChange: resolve };
}
