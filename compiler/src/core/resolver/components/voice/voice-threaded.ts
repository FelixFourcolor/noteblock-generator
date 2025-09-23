import { on } from "node:events";
import { parentPort, Worker, workerData } from "node:worker_threads";
import type { VoiceEntry } from "#types/schema/@";
import type { Resolution, VoiceContext } from "../types.js";

if (parentPort) {
	const { resolveVoice } = await import("./voice.js");

	const port = parentPort;
	const args = workerData as Parameters<typeof resolveVoice>;

	resolveVoice(...args).then(async ({ type, ticks }) => {
		port.postMessage(type);
		for await (const tick of ticks) {
			port.postMessage(tick);
		}
		port.postMessage("done");
	});
}

export async function resolveVoice(
	voice: VoiceEntry,
	ctx: VoiceContext,
): Promise<Resolution> {
	const worker = new Worker(import.meta.url, { workerData: [voice, ctx] });

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
