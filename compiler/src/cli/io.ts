import { mkdirSync, writeFileSync } from "node:fs";
import { readdir, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import { watch } from "chokidar";
import type { ArgumentsCamelCase } from "yargs";
import type { CompileOptions } from "./cli.js";
import { handleError, UserError } from "./error.js";

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
	handler: (args: T) => Promise<unknown>,
) {
	function isAsyncGenerator(val: any): val is AsyncGenerator {
		return val && typeof val[Symbol.asyncIterator] === "function";
	}

	function output(result: unknown, args: T) {
		if (result == null) {
			return;
		}

		if (result instanceof UserError) {
			console.error(result.message);
			return;
		}

		const stringified = JSON.stringify(result);
		if (args.out) {
			mkdirSync(dirname(args.out), { recursive: true });
			writeFileSync(args.out, `${stringified}\n`);
		} else {
			process.stdout.write(`${stringified}\n`);
		}
	}

	return async (args: T) => {
		try {
			const resultOrGen = await handler(args);
			if (!isAsyncGenerator(resultOrGen)) {
				output(resultOrGen, args);
				return;
			}
			if (!args.out) {
				throw new Error("Cannot handle generator output without output file");
			}

			const watcher = watch(args.out, { alwaysStat: true });
			const processNext = async () => {
				const { value, done } = await resultOrGen.next();
				if (done) {
					watcher.close();
				} else {
					output(value, args);
				}
			};
			processNext();
			watcher.on("change", (_, stats) => {
				// clearing output file is the signal to write new data
				if (stats?.size === 0) {
					processNext();
				}
			});
		} catch (error) {
			handleError(error);
		}
	};
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
