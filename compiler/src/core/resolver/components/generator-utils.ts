export function* zip<T>(generators: Generator<T[]>[]): Generator<T[]> {
	while (true) {
		const iterables = generators.map((gen) => gen.next());
		if (iterables.every((iter) => iter.done)) {
			return;
		}
		yield zipped(iterables);
	}
}

export async function* zipAsync<T>(
	generators: AsyncGenerator<T[]>[],
): AsyncGenerator<T[]> {
	while (true) {
		const iterables = await Promise.all(generators.map((gen) => gen.next()));
		if (iterables.every((iter) => iter.done)) {
			return;
		}
		yield zipped(iterables);
	}
}

function zipped<T>(iterables: IteratorResult<T[]>[]): T[] {
	const result: T[] = [];

	for (const { done, value } of iterables) {
		if (!done && value) {
			result.push(...value);
		}
	}

	return result;
}

export function* chain<T>(generators: Generator<T>[]): Generator<T> {
	for (const gen of generators) {
		yield* gen;
	}
}
