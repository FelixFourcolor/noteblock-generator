import { writeFileSync } from "node:fs";
import type { ArgumentsCamelCase } from "yargs";
import type { FileRef, JsonData } from "#lib/schema/types/@";
import { handleError, UserError } from "./error.js";

type Args = {
	pretty: boolean | undefined;
	out: string | undefined;
	in: string | undefined;
};

export async function getInput(args: Args): Promise<FileRef | JsonData> {
	if (args.in) {
		return `file://${args.in}`;
	}
	if (process.stdin.isTTY) {
		throw new UserError(
			"\nMissing input: Either provide file path with --in, or pipe content to stdin.",
		);
	}
	const chunks = await Array.fromAsync(process.stdin);
	const data = Buffer.concat(chunks).toString("utf8");
	return `json://${data}`;
}

export function withOutput<T extends ArgumentsCamelCase<Args>>(
	handler: (args: T) => Promise<unknown>,
) {
	return (args: T) => {
		const indent = args.pretty ? 2 : 0;
		handler(args)
			.then((data) => {
				const content = `${JSON.stringify(data, null, indent)}\n`;
				if (args.out) {
					writeFileSync(args.out, content);
				} else {
					process.stdout.write(content);
				}
			})
			.catch(handleError);
	};
}
