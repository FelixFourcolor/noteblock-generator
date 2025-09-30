import Yargs from "yargs";
import { hideBin } from "yargs/helpers";
import { getInput, withOutput } from "./io.js";

export class CLI {
	static run() {
		new CLI().buildArgs().parseAsync();
	}

	private readonly yargs = Yargs(hideBin(process.argv))
		.scriptName("nbc")
		.strict()
		.hide("version")
		.hide("help")
		.usage("Usage: $0 [options]");

	private compileHandler = withOutput(async (args) => {
		return getInput(args)
			.catch((error) => {
				this.yargs.showHelp();
				throw error;
			})
			.then(async (src) => {
				const { compile } = await import("#core/compile.js");
				return compile(src);
			});
	});

	private buildArgs() {
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
			})
			.command({ command: "$0", handler: this.compileHandler });
	}
}
