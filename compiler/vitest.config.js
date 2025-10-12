import { defineConfig } from "vitest/config";

export default defineConfig({
	test: {
		coverage: {
			include: ["dist/**/*.js"],
			exclude: ["dist/**/*.js.map"],
		},
	},
});
