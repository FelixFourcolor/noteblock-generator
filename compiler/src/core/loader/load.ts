import { pathToFileURL } from "node:url";
import { watch } from "chokidar";
import { debounce } from "lodash";
import { match, P } from "ts-pattern";
import { assert } from "typia";
import type { FileRef } from "@/types/schema";
import { loadSong } from "./song";
import type { LazySong, LoadedSong } from "./types";

export const load = loadSong;

export async function* liveLoader(
	src: FileRef,
	options: { debounce: number },
): AsyncGenerator<LazySong> {
	const entryFilePath = src.slice("file://".length);
	const dependencies = new Set<string>();
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

	const updateDependencies = (song: LoadedSong) => {
		const latest = new Set(
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
		dependencies
			.keys()
			.filter((path) => !latest.has(path))
			.forEach((path) => {
				watcher.unwatch(path);
				dependencies.delete(path);
			});
		latest
			.keys()
			.filter((path) => !dependencies.has(path))
			.forEach((path) => {
				watcher.add(path);
				dependencies.add(path);
			});
	};

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
				updateDependencies(song);
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
