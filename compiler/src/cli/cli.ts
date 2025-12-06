import Yargs from "yargs";
import { hideBin } from "yargs/helpers";
import { compileCommand, initCommand, schemaCommand } from "./commands";

export async function launchCLI(argv = hideBin(process.argv)) {
	const yargs = Yargs(argv)
		.scriptName("nbc")
		.strict()
		.hide("version")
		.hide("help")
		.usage("Noteblock compiler")
		.usage("Usage: $0 [command] [options]");

	const compile = compileCommand(yargs);
	const init = initCommand(yargs);
	const generateSchema = schemaCommand(yargs);

	return yargs
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
