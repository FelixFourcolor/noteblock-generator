import { writeFileSync } from "node:fs";
import type { ArgumentsCamelCase } from "yargs";
import type { CLIOptions } from "./cli.js";
import { handleError } from "./error.js";

export async function getInput(args: CLIOptions) {
	if (args.in) {
		return `file://${args.in}` as const;
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
			writeFileSync(args.out, `${stringified}\n`);
		} else {
			process.stdout.write(`${stringified}\n`);
		}
	};
}
