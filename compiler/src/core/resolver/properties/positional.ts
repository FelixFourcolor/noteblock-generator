import { mapValues, times } from "lodash";
import { match, P } from "ts-pattern";
import { createIs, is } from "typia";
import type {
	Delete,
	Reset,
	Positional as T_Positional,
} from "#types/schema/@";

export type Multi<T = unknown> = T[] & { __multi: true };

type IMulti<T> = {
	[K in keyof T]: OneOrMany<T[K]>;
};

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

type ProtoPositional<
	TInternal,
	TModifier,
	TTransformArgs extends Record<string, unknown>,
	TResolveArgs extends Record<string, unknown>,
	TReturn,
> = {
	readonly Default: TInternal;
	transform?: (
		current: TInternal,
		modifier: TModifier,
		args: TTransformArgs,
	) => TInternal;
	resolve?: (current: TInternal, args: TResolveArgs) => TReturn;
};
export interface Positional<
	TModifier,
	TTransformArgs extends Record<string, unknown>,
	TResolveArgs extends Record<string, unknown>,
	TReturn,
> {
	transform: TTransformArgs extends Record<string, never>
		? (modifier: T_Positional<TModifier> | undefined) => this
		: (
				modifier: T_Positional<TModifier> | undefined,
				args: IMulti<TTransformArgs>,
			) => this;
	fork: this["transform"];
	resolve: TResolveArgs extends Record<string, never>
		? () => OneOrMany<TReturn>
		: (args: IMulti<TResolveArgs>) => OneOrMany<TReturn>;
}
interface PositionalCtor<
	TModifier,
	TTransformArgs extends Record<string, unknown>,
	TResolveArgs extends Record<string, unknown>,
	TReturn,
> {
	new (): Positional<TModifier, TTransformArgs, TResolveArgs, TReturn>;
}
interface PositionalClass<
	TModifier,
	TTransformArgs extends Record<string, unknown>,
	TResolveArgs extends Record<string, unknown>,
	TReturn,
> extends PositionalCtor<TModifier, TTransformArgs, TResolveArgs, TReturn> {
	default: TResolveArgs extends Record<string, never>
		? () => TReturn
		: (args: TResolveArgs) => TReturn;
}

export type ResolvedType<T> = T extends PositionalClass<any, any, any, infer U>
	? OneOrMany<U>
	: never;

export function Positional<
	TInternal,
	TModifier = TInternal,
	TTransformArgs extends Record<string, unknown> = Record<string, never>,
	TResolveArgs extends Record<string, unknown> = Record<string, never>,
	TReturn = TInternal,
>({
	Default,
	transform = (_, modifier) => modifier as unknown as TInternal,
	resolve = (current) => current as unknown as TReturn,
}: ProtoPositional<
	TInternal,
	TModifier,
	TTransformArgs,
	TResolveArgs,
	TReturn
>): PositionalClass<TModifier, TTransformArgs, TResolveArgs, TReturn> {
	function deepcopy<T extends OneOrMany<TInternal>>(value: T): T {
		const copy = JSON.parse(JSON.stringify(value));
		if (isMulti(value)) {
			return multi(copy) as T;
		}
		return copy;
	}

	type InternalTransformArgs = IMulti<
		TTransformArgs & {
			original: TInternal;
			current: TInternal;
			modifier: TModifier;
		}
	>;

	function transformFn({
		original,
		current,
		modifier,
		...args
	}: TTransformArgs & {
		original: TInternal | undefined;
		current: TInternal | undefined;
		modifier: Reset | Delete | TModifier | null | undefined;
	}): TInternal | Delete {
		return match(modifier)
			.with(P.when(createIs<Delete>()), () => "$delete" as const)
			.with(P.when(createIs<Reset>()), () => original ?? Default)
			.with(P.nullish, () => current ?? "$delete")
			.otherwise(() =>
				transform(
					current ?? original ?? Default,
					modifier as TModifier,
					args as unknown as TTransformArgs,
				),
			);
	}

	type InternalResolveArgs = IMulti<TResolveArgs & { current: TInternal }>;

	function resolveFn({
		current,
		...args
	}: TResolveArgs & { current: TInternal }) {
		return resolve(current, args as unknown as TResolveArgs);
	}

	return class {
		private readonly original: OneOrMany<TInternal>;
		private current: OneOrMany<TInternal>;
		private readonly resolveCache = new Map<string, OneOrMany<TReturn>>();

		constructor(DefaultValue: OneOrMany<TInternal> = Default) {
			this.original = deepcopy(DefaultValue);
			this.current = deepcopy(DefaultValue);
		}

		private getTransformedCurrent(
			modifier: T_Positional<TModifier> | undefined,
			args: IMulti<TTransformArgs>,
		): OneOrMany<TInternal> {
			return match(modifier)
				.with(undefined, () => this.current)
				.with(P.when(createIs<Reset>()), () => this.original)
				.with(P.array(), (modifier) =>
					multi(
						(
							multiMap(transformFn, {
								original: this.original,
								current: this.current,
								modifier: multi(modifier as unknown[]),
								...args,
							} as InternalTransformArgs) as Multi<TInternal | Delete>
						).filter((value): value is TInternal => !is<Delete>(value)),
					),
				)
				.otherwise(
					() =>
						multiMap(transformFn, {
							original: this.original,
							current: this.current,
							modifier,
							...args,
						} as InternalTransformArgs) as TInternal,
				);
		}

		static default(args: TResolveArgs = {} as TResolveArgs): TReturn {
			return resolve(Default, args);
		}

		transform(
			modifier: T_Positional<TModifier> | undefined,
			args: IMulti<TTransformArgs> = {} as IMulti<TTransformArgs>,
		) {
			if (modifier !== undefined) {
				this.resolveCache.clear();
				this.current = this.getTransformedCurrent(modifier, args);
			}
			return this;
		}

		fork(
			modifier: T_Positional<TModifier> | undefined,
			args: IMulti<TTransformArgs> = {} as IMulti<TTransformArgs>,
		) {
			const ctor = this.constructor as new (
				value: OneOrMany<TInternal>,
			) => this;
			return new ctor(this.getTransformedCurrent(modifier, args));
		}

		resolve(
			args: IMulti<TResolveArgs> = {} as IMulti<TResolveArgs>,
		): OneOrMany<TReturn> {
			const cacheKey = JSON.stringify(args);
			const cached = this.resolveCache.get(cacheKey);
			if (cached !== undefined) {
				return cached;
			}

			let resolveCurrent = this.current;
			if (isMulti(this.current)) {
				const argsLength = Math.max(
					0,
					...Object.values(args)
						.filter(isMulti)
						.map((v) => v.length),
				);
				const currentLength = this.current.length;
				if (currentLength < argsLength) {
					resolveCurrent = multi([
						...this.current,
						...times(argsLength - currentLength, (i) =>
							isMulti(this.original)
								? (this.original[currentLength + i] ?? Default)
								: this.original,
						),
					]);
				}
			}

			const result = multiMap(resolveFn, {
				current: resolveCurrent,
				...args,
			} as InternalResolveArgs);
			this.resolveCache.set(cacheKey, result);
			return result;
		}
	} as unknown as PositionalClass<
		TModifier,
		TTransformArgs,
		TResolveArgs,
		TReturn
	>;
}
