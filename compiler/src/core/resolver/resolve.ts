import { basename, dirname } from "node:path";
import { watch } from "chokidar";
import { resolveSong, type SongResolution } from "#core/resolver/components/@";
import type { FileRef, JsonData } from "#schema/@";
import { ResolutionCache } from "./cache.js";

export function resolve(
	src: FileRef,
	option: { watch: true },
): AsyncGenerator<SongResolution>;

export function resolve(src: FileRef | JsonData): Promise<SongResolution>;

export function resolve(src: FileRef | JsonData, option?: { watch: true }) {
	if (!option?.watch) {
		return resolveSong(src);
	}

	return (async function* (): AsyncGenerator<SongResolution> {
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

				const resolution = await resolveSong(src, cache);
				cache.dependencies.forEach((path) => {
					if (!trackedDependencies.has(path)) {
						watcher.add(path);
						trackedDependencies.add(path);
					}
				});
				yield resolution;
			}
		} finally {
			watcher.close();
		}
	})();
}
