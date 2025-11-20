import { on } from "node:events";
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

	return (async function* () {
		const entryFilePath = src.slice(7);
		const watcher = watch(basename(entryFilePath), {
			cwd: dirname(entryFilePath),
		});
		const changeEventEmitter = on(watcher, "change");
		watcher.emit("change", entryFilePath); // trigger initial run

		const watchedFiles = new Set<string>();
		const cache = new ResolutionCache();
		try {
			for await (const [filePath] of changeEventEmitter) {
				console.log(`File changed: ${filePath}`);
				cache.invalidate(filePath);
				const resolution = await resolveSong(src, cache);
				cache.dependencies.forEach((path) => {
					if (!watchedFiles.has(path)) {
						watcher.add(path);
						watchedFiles.add(path);
					}
				});
				yield resolution;
			}
		} finally {
			watcher.close();
		}
	})();
}
