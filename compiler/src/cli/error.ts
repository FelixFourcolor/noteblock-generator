import { match, P } from "ts-pattern";

export function handleError(error: unknown) {
	match(error)
		.with(P.instanceOf(UserError), (userError) => {
			process.stderr.write(`${userError.message}\n`);
			process.exitCode = 2;
		})
		.with(P.instanceOf(Error), (programError) => {
			process.stderr.write(`${programError.stack}\n`);
			process.exitCode = 1;
		})
		.otherwise((unknownError) => {
			process.stderr.write(`Error: ${unknownError}\n`);
			process.exitCode = 3;
		});
}

export class UserError extends Error {}
