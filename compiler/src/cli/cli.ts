import Yargs, { type Argv } from "yargs";
import { hideBin } from "yargs/helpers";
import { UserError } from "./error.js";
import { getInput, withOutput } from "./io.js";

export type CLIOptions = Awaited<
	ReturnType<ReturnType<CLI["buildOptions"]>["parseAsync"]>
>;

export class CLI {
	static run(argv?: string[]) {
		return new CLI(argv).execute();
	}

	private readonly yargs: Argv;

	constructor(argv = hideBin(process.argv)) {
		this.yargs = Yargs(argv)
			.scriptName("nbc")
			.strict()
			.hide("version")
			.hide("help")
			.usage("Usage: $0 [options]");
	}

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
			})
			.option("schema", {
				type: "boolean",
				describe: "Generate schema for music source",
			})
			.option("debug", {
				choices: ["resolve", "assemble", "compile", true] as const,
				hidden: true,
			});
	}

	private handler = withOutput(async (args) => {
		if (args.schema) {
			const { generate } = await import("#schema-generator/generate.js");
			return generate();
		}

		const src = await getInput(args);
		if (!src) {
			this.yargs.showHelp();
			throw new UserError(
				"\nMissing input: Either provide file path with --in, or pipe content to stdin.",
			);
		}
		const { compile } = await import("#core/compile.js");
		const mode = args.debug === true ? "compile" : args.debug;
		return compile(src, mode);
	});

	private async execute() {
		await this.buildOptions()
			.command({ command: "$0", handler: this.handler })
			.parseAsync();
	}
}
