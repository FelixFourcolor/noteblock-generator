import { on } from "node:events";
import { parentPort, Worker, workerData } from "node:worker_threads";
import type { VoiceEntry } from "#types/schema/@";
import type { VoiceContext, VoiceResolution } from "../resolution.js";

if (parentPort) {
	const { resolveVoice } = await import("./voice.js");

	const port = parentPort;
	const args = workerData as Parameters<typeof resolveVoice>;

	resolveVoice(...args).then(async ({ time: width, type, ticks }) => {
		port.postMessage({ width, type });
		for await (const tick of ticks) {
			port.postMessage(tick);
		}
		port.postMessage("done");
	});
}

export async function resolveVoice(
	voice: VoiceEntry,
	ctx: VoiceContext,
): Promise<VoiceResolution> {
	const workerURL = new URL(import.meta.url);
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

	const { time, type } = (await messages.next()).value;

	return { time, type, ticks: messages };
}
