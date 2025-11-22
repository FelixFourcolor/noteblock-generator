import { basename, dirname } from "node:path";
import { watch } from "chokidar";
import { resolveSong, type SongResolution } from "#core/resolver/components/@";
import type { FileRef, JsonData } from "#schema/@";
import { ResolutionCache } from "./cache.js";

export function resolve(src: FileRef | JsonData): Promise<SongResolution> {
	return resolveSong(src);
}

type Resolver = () => Promise<SongResolution>;

export async function* resolveWatch(src: FileRef): AsyncGenerator<Resolver> {
	const entryFilePath = src.slice(7);
	const trackedDependencies = new Set<string>();
	const changedFiles = new Set([entryFilePath]);
	const cache = new ResolutionCache();

	let changeSignal: (() => void) | null = null;
	const watcher = watch(basename(entryFilePath), {
		cwd: dirname(entryFilePath),
	});
	watcher.on("change", (filePath) => {
		changedFiles.add(filePath);
		changeSignal?.();
		changeSignal = null;
	});

	try {
		while (true) {
			while (changedFiles.size === 0) {
				await new Promise<void>((resolve) => {
					changeSignal = resolve;
				});
			}

			changedFiles.forEach((filePath) => {
				changedFiles.delete(filePath);
				cache.invalidate(filePath);
			});

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
