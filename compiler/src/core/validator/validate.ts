import { readFile } from "node:fs/promises";
import { basename, dirname, extname, resolve as resolvePath } from "node:path";
import { is } from "typia";
import { parse as parseYAML } from "yaml";
import type { Deferred, FileRef, JsonData } from "#schema/@";

type Validator<T> = (input: unknown) => input is T;

type ValidateContext<T extends object> = {
	data: Deferred<T, { allowJson: true }>;
	validator: Validator<T>;
	cwd?: string;
};

export type Validated<T> = {
	data: T;
	cwd: string;
	filename?: string;
};

export type ValidateError = { error: string };

export async function validate<T extends object>({
	data,
	validator,
	cwd = process.cwd(),
}: ValidateContext<T>): Promise<Validated<T> | ValidateError> {
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

	if (is<JsonData>(data)) {
		const result = parseValidate(data.slice(7), validator);
		return { ...result, cwd };
	}

	return { data, cwd };
}

function filename(path: string) {
	return basename(path, extname(path));
}

async function loadValidate<T>(path: string, validator: Validator<T>) {
	let fileContent: string;
	try {
		fileContent = await readFile(path, "utf-8");
	} catch {
		return { error: `Unable to read file at "${path}".` };
	}
	return parseValidate(fileContent, validator);
}

function parseValidate<T>(input: string, validator: Validator<T>) {
	let data: unknown;
	try {
		data = parseYAML(input);
	} catch (e) {
		return { error: String(e) };
	}
	return validateWithError(data, validator);
}

function validateWithError<T>(data: unknown, validator: Validator<T>) {
	if (validator(data)) {
		return { data };
	}
	return { error: "Data does not match schema." };
}
