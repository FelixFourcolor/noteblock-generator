import Yargs from "yargs";
import { hideBin } from "yargs/helpers";
import { UserError } from "./error.js";
import { getInput, withOutput } from "./io.js";

export type CLIOptions = Awaited<
	ReturnType<ReturnType<CLI["buildOptions"]>["parseAsync"]>
>;

export class CLI {
	run() {
		this.buildOptions()
			.command({ command: "$0", handler: this.commandHandler })
			.parseAsync();
	}

	private readonly yargs = Yargs(hideBin(process.argv))
		.scriptName("nbc")
		.strict()
		.hide("version")
		.hide("help")
		.usage("Usage: $0 [options]");

	private buildOptions() {
		return this.yargs
			.option("in", {
				alias: "i",
				type: "string",
				describe: "Path to music source",
				defaultDescription: "read from stdin",
			})
			.option("out", {
				alias: "o",
				type: "string",
				describe: "Path to output file",
				defaultDescription: "write to stdout",
			});
	}

	private readonly commandHandler = withOutput(async (args) => {
		const src = await getInput(args);
		if (src) {
			const { compile } = await import("#core/compile.js");
			return compile(src);
		}

		this.yargs.showHelp();
		throw new UserError(
			"\nMissing input: Either provide file path with --in, or pipe content to stdin.",
		);
	});
}
