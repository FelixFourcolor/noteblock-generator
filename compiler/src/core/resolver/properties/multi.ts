import { mapValues, times } from "lodash";

export type Multi<T = unknown> = T[] & { __multi: true };

export type IMulti<T> = { [K in keyof T]: OneOrMany<T[K]> };

export type OneOrMany<T> = T | Multi<T>;

export function multi<T>(array: T[]): Multi<T> {
	return Object.assign(array, { __multi: true as const });
}

export function isMulti<T>(value: OneOrMany<T>): value is Multi<T> {
	return Array.isArray(value) && "__multi" in value;
}

export function multiMap<TArgs extends Record<string, unknown>, TReturn>(
	fn: (args: TArgs) => TReturn,
	args: IMulti<TArgs>,
): OneOrMany<TReturn> {
	const values = Object.values(args);

	if (!values.some(isMulti)) {
		return fn(args as TArgs);
	}

	const maxLength = Math.max(
		...values.map((value) => (isMulti(value) ? value.length : 0)),
	);

	return multi(
		times(maxLength, (i) => {
			return fn(
				mapValues(args, (value) =>
					isMulti(value) ? value[i] : value,
				) as TArgs,
			);
		}),
	);
}
