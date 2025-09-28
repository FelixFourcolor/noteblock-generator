import { UserError } from "#cli/error.js";
import type { IMeasure } from "#core/resolver/@";

export class ErrorTracker {
	private readonly errors = new Map<string, Set<string>>();

	registerError = ({
		measure,
		error,
	}: {
		measure: IMeasure;
		error: string | Error;
	}) => {
		const key = JSON.stringify(measure);
		const message = typeof error === "string" ? error : error.message;

		if (this.errors.has(key)) {
			this.errors.get(key)!.add(message);
		} else {
			this.errors.set(key, new Set([message]));
		}
	};

	validate() {
		if (this.errors.size) {
			return new UserError(this.formatErrorMessage());
		}
	}

	private formatErrorMessage() {
		const lines: string[] = [];

		this.errors.forEach((errorSet, key) => {
			const { bar, tick } = JSON.parse(key) as IMeasure;
			lines.push(`ERROR @(${bar}, ${tick}):`);

			errorSet.forEach((error) => {
				lines.push(`  - ${error}`);
			});

			lines.push("");
		});

		return lines.slice(0, -1).join("\n");
	}
}
