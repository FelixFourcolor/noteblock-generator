import { pathToFileURL } from "node:url";
import { watch } from "chokidar";
import { debounce } from "lodash";
import { match, P } from "ts-pattern";
import { assert } from "typia";
import { UserError } from "#cli/error.js";
import type { FileRef } from "#schema/@";
import { loadSong } from "./song.js";
import type { JsonString, LazySong, LoadedSong } from "./types.js";

export async function load(src: FileRef | JsonString): Promise<LoadedSong> {
	const result = await loadSong(src);
	return match(result)
		.with({ error: P.select() }, (error) => {
			throw new UserError(error);
		})
		.otherwise((loadedSong) => loadedSong);
}

export async function* liveLoader(
	src: FileRef,
	options: { debounce: number },
): AsyncGenerator<LazySong> {
	const entryFilePath = src.slice("file://".length);
	const currentDependencies = new Set<string>();
	const changedFiles = new Set([entryFilePath]);

	const createChangeSignal = () => {
		const { promise, resolve } = Promise.withResolvers<void>();
		return [promise, debounce(resolve, options.debounce)] as const;
	};
	let [nextChange, signalChange] = createChangeSignal();

	const watcher = watch(entryFilePath);
	watcher.on("change", (filePath) => {
		changedFiles.add(filePath);
		signalChange();
	});

	let song: LoadedSong | undefined;

	const fetchNext = async () => {
		if (!changedFiles.size) {
			await nextChange;
			[nextChange, signalChange] = createChangeSignal();
		}

		const songFileChanged = changedFiles.delete(entryFilePath);
		if (songFileChanged) {
			song = undefined;
		}
		const updates = Array.from(changedFiles).map(toFileRef);
		changedFiles.clear();

		return async () => {
			if (!song) {
				song = await load(src);
				const latestDependencies = new Set(
					song.voices
						.map((entry) =>
							match(entry)
								.with(null, () => [])
								.with(P.array(), (group) => group)
								.otherwise((v) => [v]),
						)
						.flat()
						.map((voice) => voice.url)
						.filter((url) => url != null)
						.map((url) => url.slice("file://".length)),
				);
				currentDependencies
					.keys()
					.filter((path) => !latestDependencies.has(path))
					.forEach((path) => {
						watcher.unwatch(path);
						currentDependencies.delete(path);
					});
				latestDependencies
					.keys()
					.filter((path) => !currentDependencies.has(path))
					.forEach((path) => {
						watcher.add(path);
						currentDependencies.add(path);
					});
			}
			return { song, updates };
		};
	};

	try {
		while (true) {
			yield await fetchNext();
		}
	} finally {
		watcher.close();
	}
}

function toFileRef(filePath: string): FileRef {
	return assert<FileRef>(pathToFileURL(filePath).href);
}
