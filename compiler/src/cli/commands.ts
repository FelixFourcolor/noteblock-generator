import { fstatSync } from "node:fs";
import { stdout } from "node:process";
import { assert } from "typia";
import type { Argv } from "yargs";
import { hideBin } from "yargs/helpers";
import { compile, liveCompiler } from "@/core/compile";
import { initProject } from "@/extras/project-init";
import { generateSchema } from "@/extras/schema-generator";
import type { FileRef } from "@/types/schema";
import { UserError } from "./error";
import { getInput, withOutput } from "./io";

export type CommandOptions<T> = Awaited<ReturnType<Argv<T>["parseAsync"]>>;

interface Command<T> {
	buildOptions(yargs: Argv): Argv<T>;
	execute(args: CommandOptions<T>): Promise<void>;
}

function createCommand<T>(recipe: {
	buildOptions: (yargs: Argv) => Argv<T>;
	execute: (args: CommandOptions<T>, yargs: Argv) => Promise<unknown>;
}): (yargs: Argv) => Command<T> {
	return (yargs) => ({
		buildOptions: recipe.buildOptions,
		execute: withOutput((args) => recipe.execute(args, yargs)),
	});
}

export const compileCommand = createCommand({
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
				describe:
					"Watch source and recompile on changes; accept an optional debounce time in ms",
				implies: "in",
				defaultDescription: "off / 1000ms",
			})
			.option("walkable", {
				choices: [true, "partial"] as const,
				describe: "Include walkable space above the build",
				defaultDescription: "false",
			})
			.option("side-padding", {
				type: "boolean",
				describe:
					"Include columns of empty space around the build; defensive against external interference",
				default: false,
			})
			.option("instrument-base", {
				type: "boolean",
				describe: "Include instrument base blocks (e.g. wool for guitar)",
				default: false,
			});
	},
	async execute(args, yargs) {
		if (hideBin(process.argv).length === 0) {
			yargs.showHelp();
			return;
		}

		const src = await getInput(args);
		const { watch, out } = args;

		if (watch === undefined) {
			return compile(src, args);
		}

		if (!out && fstatSync(stdout.fd).isFile()) {
			throw new UserError(
				"Cannot pipe to a file in watch mode; did you mean to use --out ?",
			);
		}
		const debounce = (() => {
			if (watch === true) {
				return 1000;
			}
			if (typeof watch !== "number") {
				throw new UserError(`Invalid debounce value: ${watch}`);
			}
			return Math.max(0, watch);
		})();
		return liveCompiler(
			// src is FileRef guaranteed by `implies: "in"`
			assert<FileRef>(src),
			{ ...args, debounce, emit: out ? "full" : "diff" },
		);
	},
});

export const initCommand = createCommand({
	buildOptions(yargs) {
		return yargs
			.option("voices", {
				alias: "v",
				type: "array",
				describe: "Voice names",
			})
			.option("out", {
				alias: "o",
				type: "string",
				describe: "Path to project root",
				defaultDescription: "cwd",
			});
	},
	async execute(args) {
		return initProject(args.out, args.voices?.map(String));
	},
});

export const schemaCommand = createCommand({
	buildOptions(yargs) {
		return yargs.option("out", {
			alias: "o",
			type: "string",
			describe: "Path to output file",
			defaultDescription: "stdout",
		});
	},

	async execute() {
		return generateSchema();
	},
});
