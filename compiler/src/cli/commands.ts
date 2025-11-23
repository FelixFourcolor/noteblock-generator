import { is } from "typia";
import type { Argv } from "yargs";
import { hideBin } from "yargs/helpers";
import type { FileRef } from "#schema/@";
import { UserError } from "./error.js";
import { getInput, withOutput } from "./io.js";

export type CommandOptions<T> = Awaited<ReturnType<Argv<T>["parseAsync"]>>;

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

export const compileCommand = command({
	buildOptions(yargs) {
		return yargs
			.option("in", {
				alias: "i",
				type: "string",
				describe: "Path to music source",
				defaultDescription: "stdin",
			})
			.option("out", {
				alias: "o",
				type: "string",
				describe: "Path to output file",
				defaultDescription: "stdout",
			})
			.option("watch", {
				type: "boolean",
				describe: "Watch input and recompile on changes",
				default: false,
			});
	},
	async execute(args, yargs) {
		if (hideBin(process.argv).length === 0) {
			yargs.showHelp();
			return;
		}

		if (!args.watch) {
			const src = await getInput(args);
			const { compile } = await import("#core/compile.js");
			return compile(src);
		}

		if (!args.in) {
			throw new UserError("Input required: Provide file path with --in.");
		}
		const { compile } = await import("#core/compile.js");
		return compile(`file://${args.in}`, {
			watchMode: args.out ? "full" : "diff",
		});
	},
});

export const initCommand = command({
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
		const { initProject } = await import("#extras/project-init/@");
		return initProject(args.voices?.map(String), args.out);
	},
});

export const schemaCommand = command({
	buildOptions(yargs) {
		return yargs.option("out", {
			alias: "o",
			type: "string",
			describe: "Path to output file",
			defaultDescription: "stdout",
		});
	},

	async execute() {
		const { generateSchema } = await import("#extras/schema-generator/@");
		return generateSchema();
	},
});
