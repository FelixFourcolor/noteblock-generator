import { basename, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { assert, createEquals, is } from "typia";
import type { FileRef, Notes, Voice } from "#schema/@";
import type { LazyVoice } from "./types.js";
import { validate } from "./validate.js";

export function loadVoice(
	voiceData: Voice<"lazy"> | FileRef,
	cwd: string,
): LazyVoice {
	const inferredName = inferName(voiceData);

	if (is<FileRef>(voiceData)) {
		const url = resolveUrl(voiceData, cwd);
		const load = async () => {
			const validateResult = await validate(
				voiceData,
				createEquals<Voice<"lazy", "standalone">>(),
				cwd,
			);

			if ("error" in validateResult) {
				const { error } = validateResult;
				const name = inferredName;
				return name ? { error, context: { name } } : { error };
			}

			const { validated: voice, filename } = validateResult;
			const { notes, ...modifier } = voice;
			return {
				notes,
				modifier,
				name: filename ?? inferredName,
			};
		};
		return { load, url };
	}

	const { notes: notesData, ...modifier } = voiceData;
	if (is<FileRef>(notesData)) {
		const url = resolveUrl(notesData, cwd);
		const load = async () => {
			const validateResult = await validate(
				notesData,
				createEquals<Notes<"lazy">>(),
				cwd,
			);

			if ("error" in validateResult) {
				const { error } = validateResult;
				const name = inferredName;
				return name ? { error, context: { name } } : { error };
			}

			const { validated: notes, filename } = validateResult;
			return {
				notes,
				modifier,
				name: filename ?? inferredName,
			};
		};
		return { load, modifier, url };
	}

	const loadedVoice = {
		notes: notesData,
		modifier,
		name: inferredName,
	};
	return { load: () => Promise.resolve(loadedVoice), modifier };
}

function inferName(voice: Voice<"lazy"> | Notes<"lazy"> | FileRef) {
	if (is<FileRef>(voice)) {
		return basename(voice.slice("file://".length), ".yaml");
	}
	if ("notes" in voice) {
		return inferName(voice.notes);
	}
	return undefined;
}

function resolveUrl(fileRef: FileRef, cwd: string): FileRef {
	const filePath = resolve(cwd, fileRef.slice("file://".length));
	return assert<FileRef>(pathToFileURL(filePath).href);
}
