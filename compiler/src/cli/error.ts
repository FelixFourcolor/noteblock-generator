import { match, P } from "ts-pattern";

export function handleError(error: unknown) {
	match(error)
		.with(P.instanceOf(UserError), (userError) => {
			process.stderr.write(`${userError.message}\n`);
			process.exitCode = 2;
		})
		.otherwise((error) => {
			const details = error instanceof Error ? error.stack : String(error);
			process.stderr.write(`[Unhandled error] ${details}\n`);
			process.exitCode = 3;
		});
}

export class UserError extends Error {}
