import { basename, dirname } from "node:path";
import { watch } from "chokidar";
import { debounce } from "lodash";
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

	const createChangeSignal = () => {
		const { promise, resolve } = Promise.withResolvers<void>();
		return [promise, debounce(resolve, 500)] as const;
	};
	let [nextChange, signalChange] = createChangeSignal();

	const watcher = watch(basename(entryFilePath), {
		cwd: dirname(entryFilePath),
	});
	watcher.on("change", (filePath) => {
		changedFiles.add(filePath);
		signalChange();
	});

	const refresh = async () => {
		if (!changedFiles.size) {
			await nextChange;
			[nextChange, signalChange] = createChangeSignal();
		}
		changedFiles.forEach((filePath) => {
			cache.invalidate(filePath);
		});
		changedFiles.clear();

		return async () => {
			const resolution = await resolveSong(src, cache);
			cache.dependencies.forEach((path) => {
				if (!trackedDependencies.has(path)) {
					watcher.add(path);
					trackedDependencies.add(path);
				}
			});
			return resolution;
		};
	};

	try {
		while (true) {
			yield await refresh();
		}
	} finally {
		watcher.close();
	}
}
