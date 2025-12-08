import { mkdirSync, writeFileSync } from "node:fs";
import { readdir, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import { stdin, stdout } from "node:process";
import type { FileRef } from "@/types/schema";
import type { CommandOptions } from "./commands";
import { handleError, UserError } from "./error";

export async function getInput(
	args: CommandOptions<{ in: string | undefined }>,
) {
	if (args.in) {
		const path = await getEntryPath(args.in);
		return `file://${path}` as FileRef;
	}
	if (!stdin.isTTY) {
		const chunks = await Array.fromAsync(stdin);
		const data = Buffer.concat(chunks).toString("utf8");
		return `json://${data}` as const;
	}
	throw new UserError(
		"Input required: Provide file path with --in, or pipe data to stdin.",
	);
}

export function withOutput<
	T extends CommandOptions<{ out?: string; pretty?: boolean }>,
>(executor: (args: T) => Promise<unknown>) {
	function isAsyncGenerator(val: any): val is AsyncGenerator {
		return val && typeof val[Symbol.asyncIterator] === "function";
	}

	async function emit(payload: unknown, { out }: T) {
		if (payload == null) {
			return;
		}
		// In watch mode, generator treats \n as payload separator.
		const stringified = `${JSON.stringify(payload)}\n`;

		if (out) {
			mkdirSync(dirname(out), { recursive: true });
			writeFileSync(out, stringified);
			return;
		}

		if (stdout.writableNeedDrain) {
			await new Promise((res) => stdout.once("drain", res));
		}
		stdout.write(stringified);
	}

	async function executorHandler(args: T) {
		const result = await executor(args);

		if (!isAsyncGenerator(result)) {
			return emit(result, args);
		}

		stdout.on("error", (err) => {
			if (err.code === "EPIPE") {
				process.exit(0);
			}
			throw err;
		});

		for await (const payload of result) {
			await emit(payload, args);
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
	return join(dirPath, "index.yaml");
}
