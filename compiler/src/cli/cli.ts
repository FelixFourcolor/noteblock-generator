import Yargs, { type Argv } from "yargs";
import { hideBin } from "yargs/helpers";
import { getInput, withOutput } from "./io.js";

export type CompileOptions = CommandOptions<{
	in: string | undefined;
	out: string | undefined;
}>;

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
			.usage("Usage: $0 [command] [options]");
	}

	private compileCommand = command({
		buildOptions(yargs) {
			return yargs
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
		},
		async execute(args, yargs) {
			const src = await getInput(args);
			if (!src) {
				yargs.showHelp();
				return;
			}
			const { compile } = await import("#core/compile.js");
			return compile(src);
		},
	});

	private initCommand = command({
		buildOptions(yargs) {
			return yargs
				.option("voices", {
					alias: "v",
					type: "array",
					describe: "Voice names",
					default: [],
				})
				.option("out", {
					alias: "o",
					type: "string",
					describe: "Path to project root",
					default: ".",
				});
		},
		async execute(args) {
			const { initProject } = await import("#utils/project-init/@");
			return initProject(args.voices?.map(String), args.out);
		},
	});

	private async execute() {
		const compile = this.compileCommand(this.yargs);
		const init = this.initCommand(this.yargs);

		await this.yargs
			.command({
				command: "$0",
				describe: "Compile music source",
				builder: compile.buildOptions,
				handler: compile.execute,
			})
			.command({
				command: "init",
				describe: "Initialize a new project",
				builder: init.buildOptions,
				handler: init.execute,
			})
			.parseAsync();
	}
}

type CommandOptions<T> = Awaited<ReturnType<Argv<T>["parseAsync"]>>;

interface Command<T> {
	buildOptions(yargs: Argv): Argv<T>;
	execute(args: CommandOptions<T>): Promise<void>;
}

function command<T>(recipe: {
	buildOptions: (yargs: Argv) => Argv<T>;
	execute: (args: CommandOptions<T>, yargs: Argv) => Promise<unknown>;
}): (yargs: Argv) => Command<T> {
	return (yargs) => ({
		buildOptions: recipe.buildOptions,
		execute: withOutput((args) => recipe.execute(args, yargs)),
	});
}
