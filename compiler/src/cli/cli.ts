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

	yargs
		.command({
			command: "$0",
			describe: "Compile",
			...compileCommand,
		})
		.command({
			command: "init",
			describe: "Initialize a new project",
			...initCommand,
		})
		.command({
			command: "schema",
			describe: "Generate schema for music source",
			...schemaCommand,
		});

	if (argv.length === 0) {
		yargs.showHelp();
	} else {
		yargs.parseAsync();
	}
}
