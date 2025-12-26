export class UserError extends Error {}

export function handleError(error: unknown) {
	if (error instanceof UserError) {
		process.stderr.write(`${error.message}\n`);
		process.exitCode = 2;
	} else {
		const details = error instanceof Error ? error.stack : String(error);
		process.stderr.write(`[Unhandled error] ${details}\n`);
		process.exitCode = 1;
	}
}
