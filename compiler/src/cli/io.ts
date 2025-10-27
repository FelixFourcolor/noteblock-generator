import { mkdirSync, writeFileSync } from "node:fs";
import { readdir, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import type { ArgumentsCamelCase } from "yargs";
import type { CLIOptions } from "./cli.js";
import { handleError } from "./error.js";

export async function getInput(args: CLIOptions) {
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

export function withOutput<T extends ArgumentsCamelCase<CLIOptions>>(
	handler: (args: T) => Promise<unknown>,
) {
	return async (args: T) => {
		const result = await handler(args).catch(handleError);
		if (!result) {
			return;
		}

		const stringified = args.debug
			? JSON.stringify(result, null, 2)
			: JSON.stringify(result);

		if (args.out) {
			mkdirSync(dirname(args.out), { recursive: true });
			writeFileSync(args.out, `${stringified}\n`);
		} else {
			process.stdout.write(`${stringified}\n`);
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
