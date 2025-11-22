import { mkdirSync, writeFileSync } from "node:fs";
import { readdir, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import type { ArgumentsCamelCase } from "yargs";
import type { CompileOptions } from "./cli.js";
import { handleError } from "./error.js";

export async function getInput(args: CompileOptions) {
	if (args.in) {
		const path = await getEntryPath(args.in);
		return `file://${path}` as const;
	}
	if (!process.stdin.isTTY) {
		const chunks = await Array.fromAsync(process.stdin);
		const data = Buffer.concat(chunks).toString("utf8");
		return `json://${data}` as const;
	}
}

export function withOutput<T extends ArgumentsCamelCase<{ out?: string }>>(
	executor: (args: T) => Promise<unknown>,
) {
	function isAsyncGenerator(val: any): val is AsyncGenerator {
		return val && typeof val[Symbol.asyncIterator] === "function";
	}

	function emit(payload: unknown, { out }: T) {
		if (payload == null) {
			return;
		}
		// In watch mode, generator treats \n as payload separator.
		const stringified = `${JSON.stringify(payload)}\n`;
		if (!out) {
			const flushed = process.stdout.write(stringified);
			return !flushed;
		}
		mkdirSync(dirname(out), { recursive: true });
		writeFileSync(out, stringified);
	}

	async function executorHandler(args: T) {
		const result = await executor(args);

		if (!isAsyncGenerator(result)) {
			emit(result, args);
			return;
		}

		process.stdout.on("error", (err) => {
			if (err.code === "EPIPE") {
				process.exit(0);
			}
			throw err;
		});

		for await (const payload of result) {
			if (payload instanceof Error) {
				console.error(payload.message);
				continue;
			}
			const isBufferFull = emit(payload, args);
			if (isBufferFull) {
				await new Promise((res) => process.stdout.once("drain", res));
			}
		}
	}

	return (args: T) => executorHandler(args).catch(handleError);
}

async function getEntryPath(dirPath: string): Promise<string> {
	const isDirectory = await stat(dirPath)
		.then((st) => st.isDirectory())
		.catch(() => false);
	if (!isDirectory) {
		return dirPath;
	}

	const entries = await readdir(dirPath, { withFileTypes: true });
	const topLevelFiles = entries.filter((entry) => entry.isFile());
	if (topLevelFiles.length === 1) {
		return join(dirPath, topLevelFiles[0]!.name);
	}
	return `${dirPath}/index.yaml`;
}
