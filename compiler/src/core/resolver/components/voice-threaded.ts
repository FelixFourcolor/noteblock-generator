import { on } from "node:events";
import { Worker } from "node:worker_threads";
import type { VoiceEntry } from "#core/types/@";
import type { VoiceContext, VoiceResolution } from "./voice.js";

export async function resolveVoice(
	voice: VoiceEntry,
	ctx: VoiceContext,
): Promise<VoiceResolution> {
	const workerURL = new URL("./voice.js", import.meta.url);
	const worker = new Worker(workerURL, { workerData: [voice, ctx] });

	const messages = (async function* () {
		try {
			for await (const [message] of on(worker, "message")) {
				if (message === "done") {
					return;
				}
				yield message;
			}
		} finally {
			await worker.terminate();
		}
	})();

	return {
		type: (await messages.next()).value,
		ticks: messages,
	};
}
