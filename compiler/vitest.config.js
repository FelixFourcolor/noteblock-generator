import { defineConfig } from "vitest/config";

export default defineConfig({
	test: {
		coverage: {
			provider: "v8",
			include: ["dist/**/*.js"],
			exclude: ["dist/**/*.js.map"],
		},
	},
});
