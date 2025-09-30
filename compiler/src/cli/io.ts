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
	return (args: T) => {
		handler(args)
			.then((data) => {
				const content = `${JSON.stringify(data)}\n`;
				if (args.out) {
					writeFileSync(args.out, content);
				} else {
					process.stdout.write(content);
				}
			})
			.catch(handleError);
	};
}
