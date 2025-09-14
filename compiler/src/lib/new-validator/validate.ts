import { readFile } from "node:fs/promises";
import { basename, dirname, extname, resolve as resolvePath } from "node:path";
import { type Type, type } from "arktype";
import { parse as parseYAML } from "yaml";
import { type Deferred, FileRef, JsonData } from "#lib/new-schema/@";
import { is } from "./is.js";

type ValidateContext<T extends object> = {
	data: Deferred<T>;
	validator: Type<T>;
	cwd?: string;
};

type Validated<T> = {
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
	if (is<FileRef>(FileRef, data)) {
		const cleanedPath = data.slice(7);
		const resolvedPath = resolvePath(cwd, cleanedPath);

		const result = await loadValidate(resolvedPath, validator);
		return {
			...result,
			cwd: dirname(resolvedPath),
			filename: filename(resolvedPath),
		};
	}

	if (is<JsonData>(JsonData, data)) {
		const result = parseValidate(data.slice(7), validator);
		return { ...result, cwd };
	}

	return { data, cwd };
}

function filename(path: string) {
	return basename(path, extname(path));
}

async function loadValidate<T>(path: string, validator: Type<T>) {
	let fileContent: string;
	try {
		fileContent = await readFile(path, "utf-8");
	} catch {
		return { error: `Unable to read file at "${path}".` };
	}
	return parseValidate(fileContent, validator);
}

function parseValidate<T>(input: string, validator: Type<T>) {
	let data: unknown;
	try {
		data = parseYAML(input);
	} catch (e) {
		return { error: String(e) };
	}
	return validateWithError(data, validator);
}

function validateWithError<T>(data: unknown, validator: Type<T>) {
	const result = validator(data);
	if (result instanceof type.errors) {
		return { error: result.summary };
	}
	return { data: result as T };
}
