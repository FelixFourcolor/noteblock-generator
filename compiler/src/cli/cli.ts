import { is } from "typia";
import Yargs, { type Argv } from "yargs";
import { hideBin } from "yargs/helpers";
import type { FileRef } from "#schema/@";
import { UserError } from "./error.js";
import { getInput, withOutput } from "./io.js";

export type CompileOptions = CommandOptions<{
	in: string | undefined;
	out: string | undefined;
}>;

const CLI_ARGUMENTS = hideBin(process.argv);

export class CLI {
	static run(argv?: string[]) {
		return new CLI(argv).execute();
	}

	private readonly yargs: Argv;
	constructor(argv = CLI_ARGUMENTS) {
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
				})
				.option("watch", {
					type: "boolean",
					describe: "Watch input and recompile on changes",
					default: false,
				});
		},
		async execute(args, yargs) {
			if (CLI_ARGUMENTS.length === 0) {
				yargs.showHelp();
				return;
			}

			const src = await getInput(args);

			if (args.watch) {
				if (!is<FileRef>(src)) {
					throw new UserError(
						"Missing input: --watch requires a file path with --in.",
					);
				}
				const { compileWatch } = await import("#core/compile.js");
				return compileWatch(src, args.out ? "full" : "diff");
			}

			if (!src) {
				throw new UserError(
					"Missing input: Either provide a file path with --in, or pipe content to stdin.",
				);
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
					defaultDescription: "cwd",
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
				describe: "Compile",
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
