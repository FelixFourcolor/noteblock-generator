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
		.usage("Usage: $0 [options]");

	private compileHandler = withOutput(async (args) => {
		return getInput(args)
			.catch((error) => {
				this.yargs.showHelp();
				throw error;
			})
			.then(async (src) => {
				const { compile } = await import("#lib/compile.js");
				return compile(src);
			});
	});

	private schemaHandler = withOutput(async () => {
		const { generateSchema } = await import("#lib/schema/generator/@");
		return generateSchema();
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
			.option("pretty", {
				type: "boolean",
				describe: "Write output in human-readable format",
			})
			.help()
			.command({ command: "$0", handler: this.compileHandler })
			.command({ command: "__schema", handler: this.schemaHandler });
	}
}
