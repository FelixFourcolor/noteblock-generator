import { multi, type OneOrMany } from "#core/resolver/properties/@";

export function* zip<T>(generators: Generator<T[]>[]): Generator<T[]> {
	while (true) {
		const iterables = generators.map((gen) => gen.next());
		if (iterables.every((iter) => iter.done)) {
			return;
		}
		yield zipped(iterables);
	}
}

export function* multiZip<T>(
	generators: Generator<OneOrMany<T> | undefined>[],
): Generator<OneOrMany<T> | undefined> {
	while (true) {
		const iterables = generators.map((gen) => gen.next());
		if (iterables.every((iter) => iter.done)) {
			return;
		}

		const combined = zipped(iterables);
		if (combined.length === 0) {
			yield undefined;
		} else {
			yield multi(combined);
		}
	}
}

function zipped<T>(iterables: IteratorResult<T[] | T | undefined>[]): T[] {
	const result: T[] = [];

	for (const { done, value } of iterables) {
		if (!done && value) {
			if (Array.isArray(value)) {
				result.push(...value);
			} else if (value !== undefined) {
				result.push(value);
			}
		}
	}

	return result;
}

export function* chain<T>(generators: Generator<T>[]): Generator<T> {
	for (const gen of generators) {
		yield* gen;
	}
}
