import { readFile } from "node:fs/promises";
import { basename, dirname, extname, resolve as resolvePath } from "node:path";
import { is } from "typia";
import { parse as parseYAML } from "yaml";
import type { FileRef } from "#schema/@";
import type { JsonString } from "./types.js";

type Validator<T> = (input: unknown) => input is T;

type ValidateSuccess<T> = {
	validated: T;
	cwd: string;
	filename?: string;
};

export type ValidateError<Context extends unknown | undefined = undefined> = {
	error: string;
} & (Context extends undefined ? {} : { context?: Context });

export async function validate<T extends object>(
	data: T | FileRef | JsonString,
	validator: Validator<T>,
	cwd = process.cwd(),
): Promise<ValidateSuccess<T> | ValidateError> {
	if (is<FileRef>(data)) {
		const cleanedPath = data.slice(7);
		const resolvedPath = resolvePath(cwd, cleanedPath);

		const result = await loadValidate(resolvedPath, validator);
		return {
			...result,
			cwd: dirname(resolvedPath),
			filename: filename(resolvedPath),
		};
	}

	if (is<JsonString>(data)) {
		const result = parseValidate(data.slice(7), validator);
		return { ...result, cwd };
	}

	return { validated: data, cwd };
}

function filename(path: string) {
	return basename(path, extname(path));
}

async function loadValidate<T>(path: string, validator: Validator<T>) {
	const content = await readFile(path, "utf-8").catch(() => null);
	if (!content) {
		return { error: `Unable to read file at "${path}".` };
	}
	return parseValidate(content, validator);
}

function parseValidate<T>(input: string, validator: Validator<T>) {
	let validated: unknown;
	try {
		validated = parseYAML(input);
	} catch (e) {
		return { error: String(e) };
	}
	return validateData(validated, validator);
}

function validateData<T>(data: unknown, validator: Validator<T>) {
	const success = validator(data);
	if (success) {
		return { validated: data };
	}
	return { error: "Data does not match schema." };
}
