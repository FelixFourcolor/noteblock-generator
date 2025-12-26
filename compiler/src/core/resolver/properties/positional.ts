import { match, P } from "ts-pattern";
import { createIs, is } from "typia";
import type { Delete, Reset, Positional as T_Positional } from "@/types/schema";
import {
	type IMulti,
	isMulti,
	type Multi,
	multi,
	multiMap,
	type OneOrMany,
} from "./multi";

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

interface Positional<
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

export interface PositionalClass<
	TModifier,
	TTransformArgs extends Record<string, unknown>,
	TResolveArgs extends Record<string, unknown>,
	TReturn,
> {
	new (): Positional<TModifier, TTransformArgs, TResolveArgs, TReturn>;
	default: TResolveArgs extends Record<string, never>
		? () => TReturn
		: (args: TResolveArgs) => TReturn;
}

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
	}: TResolveArgs & { current: TInternal | undefined }): TReturn | undefined {
		if (current === undefined) {
			return undefined;
		}
		return resolve(current, args as unknown as TResolveArgs);
	}

	return class PositionalImpl {
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
			return new PositionalImpl(this.getTransformedCurrent(modifier, args));
		}

		resolve(
			args: IMulti<TResolveArgs> = {} as IMulti<TResolveArgs>,
		): OneOrMany<TReturn> {
			const cacheKey = JSON.stringify(args);
			const cached = this.resolveCache.get(cacheKey);
			if (cached !== undefined) {
				return cached;
			}

			const mappedResolution = multiMap(resolveFn, {
				current: this.current,
				...args,
			} as InternalResolveArgs);
			let result: OneOrMany<TReturn>;
			if (isMulti(mappedResolution)) {
				result = multi(
					mappedResolution.filter(
						(value): value is TReturn => value !== undefined,
					),
				);
			} else {
				result = mappedResolution as TReturn;
			}
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
