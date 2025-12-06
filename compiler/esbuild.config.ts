import { resolve } from "node:path";
import { build } from "esbuild";

await build({
	entryPoints: ["./build/main.js"],
	bundle: true,
	platform: "node",
	format: "esm",
	tsconfig: "./esbuild.tsconfig.json",
	outfile: "./dist/main.js",
	external: ["chokidar", "lodash", "ts-pattern", "typia", "yaml", "yargs"],
	nodePaths: [resolve("build")],
});
