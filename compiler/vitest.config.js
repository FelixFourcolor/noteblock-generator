import { defineConfig } from "vitest/config";

export default defineConfig({
	test: {
		include: ["test/**/*.test.js"],
		coverage: {
			provider: "v8",
			include: ["dist/**/*.js"],
			exclude: ["dist/schema-generator/**"],
		},
	},
});
