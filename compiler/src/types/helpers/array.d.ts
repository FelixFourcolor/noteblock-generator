/*
 * https://github.com/hackle/blog-rust/blob/master/sample/typescript-union-to-tuple-array
 */

export type Tuplify<Union> = PickOne<Union> extends infer Last
	? Exclude<Union, Last> extends never
		? [Last]
		: [...Tuplify<Exclude<Union, Last>>, Last]
	: never;

type PickOne<T> = InferContra<InferContra<Contra<Contra<T>>>>;

type Contra<T> = T extends T ? (arg: T) => void : never;

type InferContra<T> = [T] extends [(arg: infer I) => void] ? I : never;
