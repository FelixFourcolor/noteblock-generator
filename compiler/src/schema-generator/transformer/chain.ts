export const chain = <T>(value: T) => ({
	pipe: <U>(fn: (_: T) => U) => chain(fn(value)),
	get: () => value,
});
