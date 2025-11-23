import Yargs, { type Argv } from "yargs";
import { hideBin } from "yargs/helpers";
import { compileCommand, initCommand, schemaCommand } from "./commands.js";

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
			.usage("Noteblock compiler")
			.usage("Usage: $0 [command] [options]");
	}

	private async execute() {
		const compile = compileCommand(this.yargs);
		const init = initCommand(this.yargs);
		const generateSchema = schemaCommand(this.yargs);

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
			.command({
				command: "schema",
				describe: "Generate schema for music source",
				builder: generateSchema.buildOptions,
				handler: generateSchema.execute,
			})
			.parseAsync();
	}
}
